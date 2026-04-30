"""Download morphhb WLC OSIS XML and produce per-book JSON.

Source: https://github.com/openscriptures/morphhb (CC BY 4.0)

Output schema per book file (data/hebrew/NN.json):
  {
    "book": <0-based protestant index>,
    "osis": "Gen",
    "chapters": [
      [   # chapter 0
        {  # verse 0
          "text": "בראשית ברא ...",   # display string (cantillation kept, slashes joined)
          "words": [
            {
              "text": "בְּרֵאשִׁית",
              "translit": "bereshit",
              "morphemes": [
                {"text": "בְּ", "lemma": "b",   "morph": "HR"},
                {"text": "רֵאשִׁית", "lemma": "7225", "morph": "Ncfsa"}
              ]
            },
            ...
          ]
        }
      ],
      ...
    ]
  }

Versification: morphhb (Hebrew/Masoretic) is mapped to KJV via VerseMap.xml.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import requests
from lxml import etree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.osis_codes import OT_OSIS  # noqa: E402

from translit_he import transliterate  # noqa: E402

RAW = ROOT / "data" / "raw" / "hebrew"
OUT = ROOT / "data" / "hebrew"
BIBLE_REF = ROOT / "data" / "bible" / "pt_nvi.json"  # protestant chapter/verse shape
GLOSS_FILE = ROOT / "data" / "glosses" / "he.json"
RAW.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)

BASE = "https://raw.githubusercontent.com/openscriptures/morphhb/master/wlc"
NS = {"o": "http://www.bibletechnologies.net/2003/OSIS/namespace"}


def download_all() -> None:
    files = list(OT_OSIS) + ["VerseMap"]
    for name in files:
        path = RAW / f"{name}.xml"
        if path.is_file() and path.stat().st_size > 1000:
            continue
        url = f"{BASE}/{name}.xml"
        print(f"  ↓ {name}.xml")
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        path.write_bytes(r.content)


def load_kjv_to_wlc() -> dict[str, str]:
    """Build a {kjv_osisID: wlc_osisID} map from VerseMap.xml.

    For verses not in the map, the WLC ID equals the KJV ID.
    """
    tree = etree.parse(str(RAW / "VerseMap.xml"))
    nsmap = {"v": "http://www.APTBibleTools.com/namespace"}
    out: dict[str, str] = {}
    for v in tree.xpath("//v:verse", namespaces=nsmap):
        wlc = v.get("wlc")
        kjv = v.get("kjv")
        vtype = v.get("type", "full")
        if not wlc or not kjv:
            continue
        # Only "full" mappings are 1:1. Partials describe split verses — for
        # display we still take the WLC source so the user sees the fragment.
        if kjv not in out:
            out[kjv] = wlc
    return out


def parse_word(w_el, glosses: dict[str, str]) -> dict:
    """Convert one <w> element into our morpheme structure."""
    text = "".join(w_el.itertext()).strip()
    # Use raw morphhb fields
    lemma = w_el.get("lemma", "")
    morph = w_el.get("morph", "")
    # Strip leading "H" (Hebrew language tag) from morph
    if morph.startswith("H"):
        morph = morph[1:]

    text_parts = text.split("/")
    lemma_parts = lemma.split("/") if lemma else []
    morph_parts = morph.split("/") if morph else []

    morphemes = []
    word_gloss_parts: list[str] = []
    for i, t in enumerate(text_parts):
        if not t:
            continue
        lem = lemma_parts[i].strip() if i < len(lemma_parts) else ""
        # Strong's: leading digits in lem (e.g. "1254 a" → "1254", "b" stays as letter prefix)
        digits = ""
        for ch in lem:
            if ch.isdigit():
                digits += ch
            elif digits:
                break
        gloss = glosses.get(f"H{int(digits)}") if digits else None
        morphemes.append({
            "text": t,
            "lemma": lem,
            "morph": morph_parts[i].strip() if i < len(morph_parts) else "",
            **({"gloss": gloss} if gloss else {}),
        })
        if gloss:
            word_gloss_parts.append(gloss)

    return {
        "text": text.replace("/", ""),
        "translit": transliterate(text),
        "morphemes": morphemes,
        **({"gloss": " · ".join(word_gloss_parts)} if word_gloss_parts else {}),
    }


def parse_book(osis: str, kjv_to_wlc: dict[str, str], protestant_shape: list, glosses: dict[str, str]) -> dict:
    """Build the book using the Protestant Bible's chapter/verse counts.

    For each KJV (chapter, verse) we resolve the WLC osisID via VerseMap and
    pull the words from morphhb. Verses with no WLC equivalent come back empty.
    """
    book_idx = OT_OSIS.index(osis)
    tree = etree.parse(str(RAW / f"{osis}.xml"))
    verses_by_id: dict[str, list[dict]] = {}
    word_text_by_id: dict[str, str] = {}

    for v_el in tree.xpath("//o:verse[@osisID]", namespaces=NS):
        oid = v_el.get("osisID")
        words = []
        plain_words = []
        for w in v_el.xpath(".//o:w", namespaces=NS):
            wd = parse_word(w, glosses)
            words.append(wd)
            plain_words.append(wd["text"])
        verses_by_id[oid] = words
        word_text_by_id[oid] = " ".join(plain_words)

    chapters: list[list[dict]] = []
    for ch_idx, verses in enumerate(protestant_shape, start=1):
        chap_verses = []
        for v_idx in range(1, len(verses) + 1):
            kjv_id = f"{osis}.{ch_idx}.{v_idx}"
            wlc_id = kjv_to_wlc.get(kjv_id, kjv_id)
            words = verses_by_id.get(wlc_id) or verses_by_id.get(kjv_id) or []
            text = word_text_by_id.get(wlc_id) or word_text_by_id.get(kjv_id) or ""
            chap_verses.append({"text": text, "words": words})
        chapters.append(chap_verses)

    return {"book": book_idx, "osis": osis, "chapters": chapters}


def main() -> None:
    print("Downloading morphhb WLC files…")
    download_all()
    print("Building verse map…")
    kjv_to_wlc = load_kjv_to_wlc()
    print(f"  {len(kjv_to_wlc)} versification mappings")

    print("Loading protestant chapter/verse shape…")
    protestant = json.loads(BIBLE_REF.read_text(encoding="utf-8-sig"))

    glosses: dict[str, str] = {}
    if GLOSS_FILE.is_file():
        glosses = json.loads(GLOSS_FILE.read_text())
        print(f"Loaded {len(glosses)} Hebrew glosses")
    else:
        print("⚠ No Hebrew glosses file found — run scripts/import_glosses.py first")

    for i, osis in enumerate(OT_OSIS):
        print(f"[{i:02d}] {osis}…", end=" ", flush=True)
        shape = protestant[i]["chapters"]
        book = parse_book(osis, kjv_to_wlc, shape, glosses)
        out_path = OUT / f"{i:02d}.json"
        out_path.write_text(json.dumps(book, ensure_ascii=False, separators=(",", ":")))
        ch_count = len(book["chapters"])
        v_count = sum(len(c) for c in book["chapters"])
        print(f"{ch_count} chapters / {v_count} verses → {out_path.name}")


if __name__ == "__main__":
    main()
