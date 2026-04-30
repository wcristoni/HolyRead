"""Bible reading endpoints."""
from __future__ import annotations

import re
import unicodedata
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from ..config import RATE_LIMIT_SEARCH
from ..limiter import limiter
from ..services import data_loader as dl

router = APIRouter(prefix="/api/bible", tags=["bible"])


@router.get("/versions")
def versions() -> dict[str, Any]:
    return {"versions": dl.list_versions()}


@router.get("/{version}")
def whole_version(version: str) -> list[dict]:
    """Return the full Bible. Heavy — frontend caches in memory."""
    try:
        return dl.load_version(version)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="version not found")


@router.get("/{version}/{book}/{chapter}")
def chapter(version: str, book: int, chapter: int) -> dict[str, Any]:
    try:
        data = dl.load_version(version)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="version not found")
    if not (0 <= book < len(data)):
        raise HTTPException(status_code=404, detail="book out of range")
    chapters = data[book].get("chapters", [])
    if not (0 <= chapter < len(chapters)):
        raise HTTPException(status_code=404, detail="chapter out of range")
    return {
        "book": book,
        "chapter": chapter,
        "abbrev": data[book].get("abbrev"),
        "verses": chapters[chapter],
    }


def _norm(s: str) -> str:
    return "".join(
        c
        for c in unicodedata.normalize("NFD", s.lower())
        if unicodedata.category(c) != "Mn"
    )


@router.get("/{version}/search")
@limiter.limit(RATE_LIMIT_SEARCH)
def search(
    request: Request,
    version: str,
    q: str = Query(..., min_length=2, max_length=120),
    limit: int = Query(40, ge=1, le=100),
) -> dict[str, Any]:
    try:
        data = dl.load_version(version)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="version not found")

    q_norm = _norm(q)
    results: list[dict] = []
    for bi, book in enumerate(data):
        for ci, verses in enumerate(book.get("chapters", [])):
            for vi, text in enumerate(verses):
                if q_norm in _norm(text):
                    results.append({"book": bi, "chapter": ci, "verse": vi, "text": text})
                    if len(results) >= limit:
                        return {"q": q, "count": len(results), "results": results, "truncated": True}
    return {"q": q, "count": len(results), "results": results, "truncated": False}
