"""Centralised config loaded from environment."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / os.environ.get("DATA_DIR", "data")

# CORS — two modes:
#   1. ALLOWED_ORIGINS set      → strict allowlist (production)
#   2. ALLOWED_ORIGINS unset    → dev regex matching localhost + private LANs
_RAW_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "").strip()
if _RAW_ORIGINS:
    ALLOWED_ORIGINS = [o.strip() for o in _RAW_ORIGINS.split(",") if o.strip()]
    ALLOWED_ORIGIN_REGEX: str | None = os.environ.get("ALLOWED_ORIGIN_REGEX") or None
else:
    ALLOWED_ORIGINS = []
    # localhost · 127.x · 10.x · 172.16-31.x · 192.168.x.x · *.local — any port
    ALLOWED_ORIGIN_REGEX = (
        r"^https?://("
        r"localhost"
        r"|127\.\d{1,3}\.\d{1,3}\.\d{1,3}"
        r"|10\.\d{1,3}\.\d{1,3}\.\d{1,3}"
        r"|172\.(1[6-9]|2[0-9]|3[01])\.\d{1,3}\.\d{1,3}"
        r"|192\.168\.\d{1,3}\.\d{1,3}"
        r"|[A-Za-z0-9-]+\.local"
        r")(:\d+)?$"
    )

RATE_LIMIT_DEFAULT = os.environ.get("RATE_LIMIT_DEFAULT", "120/minute")
RATE_LIMIT_SEARCH = os.environ.get("RATE_LIMIT_SEARCH", "20/minute")

HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8000"))
