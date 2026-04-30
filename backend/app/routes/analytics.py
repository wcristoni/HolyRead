"""Lightweight, privacy-aware visit counter.

Design notes
------------
- IP is *never stored*. We hash it with a server-side salt and keep the first
  12 hex chars — enough to count unique visitors per day, not enough to
  identify a person.
- Only aggregate fields are kept (country, device, OS, day). No URL params,
  no fingerprinting, no cookies.
- ip-api.com (free tier, 45 req/min, no key) gives country code. Cached to
  stay polite.
- Storage: append-only JSONL at data/analytics/events.jsonl. Volatile across
  Railway redeploys (acceptable for V1; MongoDB sync is V2).
- /stats requires ADMIN_KEY env var.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from fastapi import APIRouter, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field

from ..config import DATA_DIR
from ..limiter import limiter

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

ANALYTICS_DIR = DATA_DIR / "analytics"
ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)
EVENTS_FILE = ANALYTICS_DIR / "events.jsonl"

# Salt is per-instance: rotates on redeploy. Stable enough for daily-uniques
# bucket, weak enough to make replay attacks across deploys useless.
ANALYTICS_SALT = os.environ.get("ANALYTICS_SALT") or hashlib.sha256(
    f"{time.time()}-{os.getpid()}".encode()
).hexdigest()[:32]
ADMIN_KEY = os.environ.get("ADMIN_KEY", "")

# Country lookup cache: { ip: (country_code, expiry_ts) }
_GEO_CACHE: dict[str, tuple[str, float]] = {}
_GEO_TTL_SEC = 24 * 3600

UA_MOBILE_RE = re.compile(
    r"\b(android|iphone|ipod|ipad|blackberry|webos|windows phone|opera mini|mobile|silk)\b",
    re.I,
)
UA_TABLET_RE = re.compile(r"\b(ipad|tablet)\b", re.I)


def _hash_ip(ip: str, day_bucket: str) -> str:
    """Stable per-day fingerprint without revealing the IP."""
    h = hashlib.sha256(f"{ip}|{day_bucket}|{ANALYTICS_SALT}".encode()).hexdigest()
    return h[:12]


def _client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        return xff.split(",")[0].strip()
    real = request.headers.get("x-real-ip")
    if real:
        return real
    return request.client.host if request.client else ""


def _detect_device(ua: str) -> str:
    if not ua:
        return "unknown"
    if UA_TABLET_RE.search(ua):
        return "tablet"
    if UA_MOBILE_RE.search(ua):
        return "mobile"
    return "desktop"


def _detect_os(ua: str) -> str:
    ua_l = (ua or "").lower()
    if "android" in ua_l:
        return "Android"
    if "iphone" in ua_l or "ipad" in ua_l or "ipod" in ua_l:
        return "iOS"
    if "mac os" in ua_l or "macintosh" in ua_l:
        return "macOS"
    if "windows" in ua_l:
        return "Windows"
    if "linux" in ua_l:
        return "Linux"
    if "cros" in ua_l:
        return "ChromeOS"
    return "Other"


def _detect_browser(ua: str) -> str:
    ua_l = (ua or "").lower()
    if "edg/" in ua_l or "edge" in ua_l:
        return "Edge"
    if "opr/" in ua_l or "opera" in ua_l:
        return "Opera"
    if "samsungbrowser" in ua_l:
        return "Samsung"
    if "firefox" in ua_l:
        return "Firefox"
    if "chrome" in ua_l:
        return "Chrome"
    if "safari" in ua_l:
        return "Safari"
    return "Other"


def _country_lookup(ip: str) -> str:
    """Return ISO-2 country code, '??' on failure. Cached for 24h per IP."""
    if not ip or ip.startswith(("127.", "10.", "192.168.", "172.")):
        return "LO"  # local network
    now = time.time()
    cached = _GEO_CACHE.get(ip)
    if cached and cached[1] > now:
        return cached[0]
    try:
        r = requests.get(
            f"http://ip-api.com/json/{ip}",
            params={"fields": "countryCode"},
            timeout=2.5,
        )
        cc = (r.json() or {}).get("countryCode") or "??"
    except Exception:
        cc = "??"
    _GEO_CACHE[ip] = (cc, now + _GEO_TTL_SEC)
    return cc


def _append_event(event: dict[str, Any]) -> None:
    with EVENTS_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


# ─────────────────────────────────────────────────────────────────────────


class PingPayload(BaseModel):
    page: str = Field(default="/", max_length=200)
    referrer: str = Field(default="", max_length=500)
    lang: str = Field(default="", max_length=10)


@router.post("/ping", status_code=204)
@limiter.limit("60/minute")
def ping(request: Request, payload: PingPayload) -> Response:
    """Record a single visit. Body fields are tightly bounded; UA + IP come
    from headers. Returns 204 even on internal errors (best-effort)."""
    try:
        ua = request.headers.get("user-agent", "")[:500]
        ip = _client_ip(request)
        now = datetime.now(timezone.utc)
        day = now.strftime("%Y-%m-%d")
        # Trim referrer to host only (strip query / path) for privacy
        ref = (payload.referrer or "")[:200]
        if ref.startswith("http"):
            try:
                from urllib.parse import urlparse
                ref = urlparse(ref).netloc[:80]
            except Exception:
                ref = ref[:80]
        event = {
            "t": now.isoformat(timespec="seconds"),
            "d": day,
            "v": _hash_ip(ip, day),
            "co": _country_lookup(ip),
            "dv": _detect_device(ua),
            "os": _detect_os(ua),
            "br": _detect_browser(ua),
            "p": payload.page[:120],
            "r": ref,
            "l": payload.lang[:10],
        }
        _append_event(event)
    except Exception:
        # Never let analytics break the user experience.
        pass
    return Response(status_code=204)


@router.get("/stats")
def stats(key: str = Query(...)) -> dict[str, Any]:
    """Aggregated stats. Protected by ADMIN_KEY env var."""
    if not ADMIN_KEY or key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="unauthorized")

    total = 0
    by_day: Counter[str] = Counter()
    by_country: Counter[str] = Counter()
    by_device: Counter[str] = Counter()
    by_os: Counter[str] = Counter()
    by_browser: Counter[str] = Counter()
    by_lang: Counter[str] = Counter()
    by_referrer: Counter[str] = Counter()
    uniques: dict[str, set[str]] = defaultdict(set)
    pages: Counter[str] = Counter()

    if EVENTS_FILE.is_file():
        with EVENTS_FILE.open(encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    e = json.loads(line)
                except Exception:
                    continue
                total += 1
                by_day[e.get("d", "")] += 1
                by_country[e.get("co", "??")] += 1
                by_device[e.get("dv", "unknown")] += 1
                by_os[e.get("os", "Other")] += 1
                by_browser[e.get("br", "Other")] += 1
                if e.get("l"):
                    by_lang[e["l"]] += 1
                if e.get("r"):
                    by_referrer[e["r"]] += 1
                pages[e.get("p", "/")] += 1
                uniques[e.get("d", "")].add(e.get("v", ""))

    return {
        "total_events": total,
        "by_day": dict(by_day.most_common()),
        "unique_visitors_per_day": {d: len(s) for d, s in uniques.items()},
        "by_country": dict(by_country.most_common()),
        "by_device": dict(by_device.most_common()),
        "by_os": dict(by_os.most_common()),
        "by_browser": dict(by_browser.most_common()),
        "by_language": dict(by_lang.most_common()),
        "top_referrers": dict(by_referrer.most_common(20)),
        "top_pages": dict(pages.most_common(20)),
    }
