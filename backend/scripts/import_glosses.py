"""Download STEPBible TBESH/TBESG and produce {strongs_number: gloss_en} JSON.

Sources (CC BY 4.0, STEPBible.org):
  TBESH — Hebrew Strong's brief glosses
  TBESG — Greek  Strong's brief glosses

We use ONLY the `Gloss` column (CC BY by Tyndale). The `Meaning` column comes
from Online Bible BDB and has separate permission requirements — skipped.

Output:
  backend/data/glosses/he.json     {"H1": "father", "H2": "father", ...}
  backend/data/glosses/grc.json    {"G13": "Agabus", ...}
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

RAW = ROOT / "data" / "raw" / "glosses"
OUT = ROOT / "data" / "glosses"
RAW.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)

URLS = {
    "H": "https://raw.githubusercontent.com/STEPBible/STEPBible-Data/master/Lexicons/"
         "TBESH%20-%20Translators%20Brief%20lexicon%20of%20Extended%20Strongs%20for%20Hebrew%20-%20STEPBible.org%20CC%20BY.txt",
    "G": "https://raw.githubusercontent.com/STEPBible/STEPBible-Data/master/Lexicons/"
         "TBESG%20-%20Translators%20Brief%20lexicon%20of%20Extended%20Strongs%20for%20Greek%20-%20STEPBible.org%20CC%20BY.txt",
}


def download(prefix: str) -> bytes:
    path = RAW / f"TBES{prefix}.txt"
    if path.is_file() and path.stat().st_size > 100_000:
        return path.read_bytes()
    print(f"  ↓ TBES{prefix}.txt")
    r = requests.get(URLS[prefix], timeout=60)
    r.raise_for_status()
    path.write_bytes(r.content)
    return r.content


def parse_tbes(raw: bytes, prefix: str) -> dict[str, str]:
    """Parse the TBESH/TBESG file. Returns {f'{prefix}{N}': gloss}."""
    text = raw.decode("utf-8-sig", errors="replace")
    out: dict[str, str] = {}
    line_re = re.compile(rf"^{prefix}(\d+)[A-Z]?")
    for line in text.splitlines():
        if not line or not line[0] == prefix:
            continue
        m = line_re.match(line)
        if not m:
            continue
        cols = line.split("\t")
        if len(cols) < 7:
            continue
        num = str(int(m.group(1)))  # strip leading zeros
        gloss = cols[6].strip()
        if not gloss:
            continue
        key = f"{prefix}{num}"
        # Keep first-seen entry (base Strong's, before extended disambiguators)
        if key not in out:
            out[key] = gloss
    return out


def main() -> None:
    for prefix, lang in [("H", "he"), ("G", "grc")]:
        print(f"Downloading TBES{prefix}…")
        raw = download(prefix)
        print(f"Parsing TBES{prefix}…")
        glosses = parse_tbes(raw, prefix)
        print(f"  {len(glosses)} entries")
        out_path = OUT / f"{lang}.json"
        out_path.write_text(json.dumps(glosses, ensure_ascii=False, separators=(",", ":")))
        print(f"  → {out_path.name} ({out_path.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
