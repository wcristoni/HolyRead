"""Lazy in-memory loaders for Bible JSON, Hebrew, Greek + per-language glosses."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any  # noqa: F401

from ..config import DATA_DIR

BIBLE_DIR = DATA_DIR / "bible"
HEBREW_DIR = DATA_DIR / "hebrew"
GREEK_DIR = DATA_DIR / "greek"

# Same 0-indexed canonical order used in the frontend.
# OT = 0..38, NT = 39..65 (66 books total).
OT_END = 38


def _read_json(path: Path) -> Any:
    text = path.read_text(encoding="utf-8-sig")  # tolerates BOM
    return json.loads(text)


@lru_cache(maxsize=16)
def load_version(version: str) -> list[dict]:
    """Return the full Bible for a translation as a list of book dicts."""
    path = BIBLE_DIR / f"{version}.json"
    if not path.is_file():
        raise FileNotFoundError(version)
    return _read_json(path)


@lru_cache(maxsize=1)
def list_versions() -> list[dict]:
    out = []
    for p in sorted(BIBLE_DIR.glob("*.json")):
        out.append({"code": p.stem})
    return out


@lru_cache(maxsize=128)
def load_hebrew_book(book_idx: int) -> dict | None:
    """Hebrew book file (morphhb-derived). Returns None if not generated yet."""
    if book_idx > OT_END:
        return None
    path = HEBREW_DIR / f"{book_idx:02d}.json"
    if not path.is_file():
        return None
    return _read_json(path)


@lru_cache(maxsize=128)
def load_greek_book(book_idx: int) -> dict | None:
    """Greek book file (MorphGNT-derived). Returns None if not generated yet."""
    if book_idx <= OT_END:
        return None
    path = GREEK_DIR / f"{book_idx:02d}.json"
    if not path.is_file():
        return None
    return _read_json(path)


# ──────────────────────────────────────────────
# GLOSSES — per language (en/pt/es/fr) × source (he/grc)
# ──────────────────────────────────────────────
GLOSS_DIR = DATA_DIR / "glosses"


@lru_cache(maxsize=16)
def load_glosses(lang: str, src: str) -> dict[str, str]:
    """src in {'he','grc'}, lang in {'en','pt','es','fr'}.

    Layout: data/glosses/{lang}/{src}.json. Falls back to legacy flat layout
    (data/glosses/{src}.json which is English-only) when lang=='en' and the
    new layout is absent.
    """
    nested = GLOSS_DIR / lang / f"{src}.json"
    if nested.is_file():
        return json.loads(nested.read_text(encoding="utf-8"))
    if lang == "en":
        legacy = GLOSS_DIR / f"{src}.json"
        if legacy.is_file():
            return json.loads(legacy.read_text(encoding="utf-8"))
    return {}


def _digits_prefix(s: str) -> str:
    """Extract the leading run of digits (e.g. '1254 a' → '1254')."""
    out = ""
    for ch in s:
        if ch.isdigit():
            out += ch
        elif out:
            break
    return out


def remap_hebrew_glosses(verse: dict, lang: str) -> dict:
    """Replace each morpheme's gloss with the requested-language version."""
    target = load_glosses(lang, "he") if lang != "en" else {}
    fallback = load_glosses("en", "he") if lang != "en" else {}
    out = {**verse, "words": []}
    for w in verse.get("words", []):
        new_w = {k: v for k, v in w.items() if k != "gloss"}
        word_glosses: list[str] = []
        morphemes = w.get("morphemes", [])
        new_morphemes = []
        for m in morphemes:
            new_m = {k: v for k, v in m.items() if k != "gloss"}
            digits = _digits_prefix(m.get("lemma", ""))
            if digits:
                sn = f"H{int(digits)}"
                g = (target.get(sn) if lang != "en" else None) or fallback.get(sn) or m.get("gloss")
                if g:
                    new_m["gloss"] = g
                    word_glosses.append(g)
            else:
                if m.get("gloss"):
                    new_m["gloss"] = m["gloss"]
                    word_glosses.append(m["gloss"])
            new_morphemes.append(new_m)
        if morphemes:
            new_w["morphemes"] = new_morphemes
        if word_glosses:
            new_w["gloss"] = " · ".join(word_glosses)
        out["words"].append(new_w)
    return out


def remap_greek_glosses(verse: dict, lang: str) -> dict:
    """Replace each word's gloss with the requested-language version."""
    target = load_glosses(lang, "grc") if lang != "en" else {}
    fallback = load_glosses("en", "grc") if lang != "en" else {}
    out = {**verse, "words": []}
    for w in verse.get("words", []):
        new_w = {k: v for k, v in w.items() if k != "gloss"}
        sn = w.get("strongs")
        if sn:
            g = (target.get(sn) if lang != "en" else None) or fallback.get(sn) or w.get("gloss")
            if g:
                new_w["gloss"] = g
        elif w.get("gloss"):
            new_w["gloss"] = w["gloss"]
        out["words"].append(new_w)
    return out
