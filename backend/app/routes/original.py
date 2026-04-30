"""Original-language (Hebrew/Greek) per-verse endpoints."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from ..services import data_loader as dl

router = APIRouter(prefix="/api/original", tags=["original"])

SUPPORTED_LANGS = {"en", "pt", "es", "fr"}


def _lang(lang: str) -> str:
    return lang if lang in SUPPORTED_LANGS else "en"


@router.get("/hebrew/{book}/{chapter}/{verse}")
def hebrew_verse(
    book: int,
    chapter: int,
    verse: int,
    lang: str = Query("en", description="UI language for word glosses (en/pt/es/fr)"),
) -> dict[str, Any]:
    if book > dl.OT_END:
        raise HTTPException(status_code=400, detail="book is not in the OT")
    bk = dl.load_hebrew_book(book)
    if bk is None:
        raise HTTPException(status_code=404, detail="hebrew data not available — run ETL")
    chapters = bk.get("chapters", [])
    if not (0 <= chapter < len(chapters)):
        raise HTTPException(status_code=404, detail="chapter out of range")
    verses = chapters[chapter]
    if not (0 <= verse < len(verses)):
        raise HTTPException(status_code=404, detail="verse out of range")
    v = dl.remap_hebrew_glosses(verses[verse], _lang(lang))
    return {
        "lang": "he",
        "ui_lang": _lang(lang),
        "ref": {"book": book, "chapter": chapter, "verse": verse},
        **v,
    }


@router.get("/greek/{book}/{chapter}/{verse}")
def greek_verse(
    book: int,
    chapter: int,
    verse: int,
    lang: str = Query("en", description="UI language for word glosses (en/pt/es/fr)"),
) -> dict[str, Any]:
    if book <= dl.OT_END:
        raise HTTPException(status_code=400, detail="book is not in the NT")
    bk = dl.load_greek_book(book)
    if bk is None:
        raise HTTPException(status_code=404, detail="greek data not available — run ETL")
    chapters = bk.get("chapters", [])
    if not (0 <= chapter < len(chapters)):
        raise HTTPException(status_code=404, detail="chapter out of range")
    verses = chapters[chapter]
    if not (0 <= verse < len(verses)):
        raise HTTPException(status_code=404, detail="verse out of range")
    v = dl.remap_greek_glosses(verses[verse], _lang(lang))
    return {
        "lang": "grc",
        "ui_lang": _lang(lang),
        "ref": {"book": book, "chapter": chapter, "verse": verse},
        **v,
    }
