"""Download MorphGNT plain-text files and produce per-book JSON.

Sources:
  - SBLGNT text:      CC-BY-4.0 (https://sblgnt.com/license/)
  - MorphGNT morph:   CC-BY-SA 3.0 (https://github.com/morphgnt/sblgnt)

Output schema per book file (data/greek/NN.json):
  {
    "book": <0-based protestant index, 39..65>,
    "osis": "Matt",
    "chapters": [
      [   # chapter 0 → list of verses
        {  # verse 0
          "text": "Βίβλος γενέσεως ...",
          "words": [
            {
              "text": "Βίβλος",
              "lemma": "βίβλος",
              "morph": "N- ----NSF-",
              "translit_eras": "biblos",
              "translit_mod": "vivlos"
            },
            ...
          ]
        }
      ],
      ...
    ]
  }

Internal book code in the bcv ID = 01..27 mapping to Matthew..Revelation.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.osis_codes import NT_FILE_PREFIX, NT_OSIS, OT_OSIS  # noqa: E402

from translit_grc import transliterate_eras, transliterate_mod  # noqa: E402

RAW = ROOT / "data" / "raw" / "greek"
OUT = ROOT / "data" / "greek"
GLOSS_FILE = ROOT / "data" / "glosses" / "grc.json"
STRONGS_DICT_PATH = RAW / "strongs-greek-dictionary.js"
RAW.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)

BASE = "https://raw.githubusercontent.com/morphgnt/sblgnt/master"
STRONGS_GREEK_URL = (
    "https://raw.githubusercontent.com/openscriptures/strongs/master/greek/"
    "strongs-greek-dictionary.js"
)

NT_OFFSET = len(OT_OSIS)  # 39


def download_all() -> None:
    for global_idx, prefix in NT_FILE_PREFIX.items():
        path = RAW / f"{prefix}-morphgnt.txt"
        if path.is_file() and path.stat().st_size > 1000:
            continue
        url = f"{BASE}/{prefix}-morphgnt.txt"
        print(f"  ↓ {prefix}-morphgnt.txt")
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        path.write_bytes(r.content)
    if not STRONGS_DICT_PATH.is_file():
        print("  ↓ strongs-greek-dictionary.js (lemma→Strong mapping)")
        r = requests.get(STRONGS_GREEK_URL, timeout=60)
        r.raise_for_status()
        STRONGS_DICT_PATH.write_bytes(r.content)


def _strip_di(s: str) -> str:
    import unicodedata
    return "".join(
        c for c in unicodedata.normalize("NFD", s.lower())
        if unicodedata.category(c) != "Mn"
    )


def build_lemma_to_strongs() -> dict[str, str]:
    """Build {lemma: G####} reverse map from openscriptures Strong's Greek."""
    import re
    text = STRONGS_DICT_PATH.read_text(encoding="utf-8")
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    m = re.search(r"var\s+strongsGreekDictionary\s*=\s*(\{.*\});", text, re.DOTALL)
    if not m:
        return {}
    data = json.loads(m.group(1))
    exact: dict[str, str] = {}
    norm: dict[str, str] = {}
    for sn, e in data.items():
        lemma = (e or {}).get("lemma") or ""
        if not lemma:
            continue
        if lemma not in exact:
            exact[lemma] = sn
        n = _strip_di(lemma)
        if n not in norm:
            norm[n] = sn
    # Combine: exact first, then normalised (strip diacritics) as fallback
    return {**norm, **exact}  # exact wins on collision


def lookup_strongs(lemma: str, lemma2sn: dict[str, str]) -> str | None:
    if lemma in lemma2sn:
        return lemma2sn[lemma]
    # MorphGNT may write οὕτω(ς) / Δαυ(ε)ίδ etc — strip parens (keep content),
    # then strip parens (drop content), then strip diacritics
    candidates = [
        lemma.replace("(", "").replace(")", ""),  # keep content
        __import__("re").sub(r"\([^)]*\)", "", lemma),  # drop content
    ]
    for c in candidates:
        if c in lemma2sn:
            return lemma2sn[c]
        nc = _strip_di(c)
        if nc in lemma2sn:
            return lemma2sn[nc]
    return lemma2sn.get(_strip_di(lemma))


def parse_book(global_idx: int, lemma2sn: dict[str, str], glosses: dict[str, str]) -> dict:
    """Build one Greek book file."""
    osis = NT_OSIS[global_idx - NT_OFFSET]
    prefix = NT_FILE_PREFIX[global_idx]
    raw_path = RAW / f"{prefix}-morphgnt.txt"

    by_chapter_verse: dict[tuple[int, int], list[dict]] = {}

    for line in raw_path.read_text(encoding="utf-8").splitlines():
        line = line.rstrip()
        if not line:
            continue
        # 040316 D- -------- Οὕτως Οὕτως οὕτω(ς) οὕτω(ς)
        parts = line.split(" ", 6)
        if len(parts) < 7:
            continue
        bcv, pos, parsing, text_punct, text_clean, normalized, lemma = parts
        # bcv = BBCCVV with B = 01..27 (NT-internal)
        try:
            ch = int(bcv[2:4])
            vs = int(bcv[4:6])
        except ValueError:
            continue
        morph_code = f"{pos} {parsing}"
        sn = lookup_strongs(lemma, lemma2sn)
        gloss = glosses.get(sn) if sn else None
        word = {
            "text": text_punct,
            "clean": text_clean,
            "lemma": lemma,
            "morph": morph_code,
            "translit_eras": transliterate_eras(text_clean),
            "translit_mod": transliterate_mod(text_clean),
            **({"strongs": sn} if sn else {}),
            **({"gloss": gloss} if gloss else {}),
        }
        by_chapter_verse.setdefault((ch, vs), []).append(word)

    if not by_chapter_verse:
        return {"book": global_idx, "osis": osis, "chapters": []}

    max_ch = max(ch for ch, _ in by_chapter_verse.keys())
    chapters: list[list[dict]] = []
    for ch in range(1, max_ch + 1):
        verse_keys = [k for k in by_chapter_verse if k[0] == ch]
        if not verse_keys:
            chapters.append([])
            continue
        max_v = max(v for _, v in verse_keys)
        ch_verses = []
        for v in range(1, max_v + 1):
            words = by_chapter_verse.get((ch, v), [])
            text = " ".join(w["text"] for w in words)
            ch_verses.append({"text": text, "words": words})
        chapters.append(ch_verses)

    return {"book": global_idx, "osis": osis, "chapters": chapters}


def main() -> None:
    print("Downloading MorphGNT + Strong's lemma map…")
    download_all()
    print("Building lemma→Strong's map…")
    lemma2sn = build_lemma_to_strongs()
    print(f"  {len(lemma2sn)} lemma entries indexed")

    glosses: dict[str, str] = {}
    if GLOSS_FILE.is_file():
        glosses = json.loads(GLOSS_FILE.read_text())
        print(f"Loaded {len(glosses)} Greek glosses")
    else:
        print("⚠ No Greek glosses file — run scripts/import_glosses.py first")

    for global_idx in sorted(NT_FILE_PREFIX.keys()):
        osis = NT_OSIS[global_idx - NT_OFFSET]
        print(f"[{global_idx:02d}] {osis}…", end=" ", flush=True)
        book = parse_book(global_idx, lemma2sn, glosses)
        out_path = OUT / f"{global_idx:02d}.json"
        out_path.write_text(json.dumps(book, ensure_ascii=False, separators=(",", ":")))
        ch_count = len(book["chapters"])
        v_count = sum(len(c) for c in book["chapters"])
        print(f"{ch_count} chapters / {v_count} verses → {out_path.name}")


if __name__ == "__main__":
    main()
