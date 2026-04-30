"""Translate STEPBible English glosses to PT/ES/FR via deep-translator (Google free).

Strategy:
- Combine all unique English glosses (Hebrew + Greek) into one set (~13k strings).
- For each target language, batch ~100 glosses joined by "\n" → one Google call.
- Save the {en→target} translation table incrementally to disk after each batch
  so a Ctrl-C / network blip doesn't lose progress.
- Re-run is idempotent: already-translated entries are skipped.

After translation, build per-language Strong's tables:
  data/glosses/{lang}/he.json   {"H1": "pai", ...}
  data/glosses/{lang}/grc.json  {"G976": "livro", ...}
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

GLOSS_DIR = ROOT / "data" / "glosses"
EN_HE = GLOSS_DIR / "he.json"
EN_GRC = GLOSS_DIR / "grc.json"
TRANS_CACHE_DIR = GLOSS_DIR / "_cache"  # {en_gloss: target_gloss} maps
TRANS_CACHE_DIR.mkdir(parents=True, exist_ok=True)

LANGS = ("pt", "es", "fr")
BATCH_SIZE = 100
DELAY_BETWEEN_BATCHES = 0.4  # seconds — be polite


def load_en_combined() -> dict[str, str]:
    he = json.loads(EN_HE.read_text())
    gr = json.loads(EN_GRC.read_text())
    return {**he, **gr}


def collect_unique_glosses(en_map: dict[str, str]) -> list[str]:
    seen = set()
    out: list[str] = []
    for v in en_map.values():
        if v not in seen:
            seen.add(v)
            out.append(v)
    return out


def load_cache(lang: str) -> dict[str, str]:
    p = TRANS_CACHE_DIR / f"en2{lang}.json"
    if p.is_file():
        return json.loads(p.read_text())
    return {}


def save_cache(lang: str, cache: dict[str, str]) -> None:
    p = TRANS_CACHE_DIR / f"en2{lang}.json"
    p.write_text(json.dumps(cache, ensure_ascii=False, separators=(",", ":")))


def translate_missing(lang: str, all_unique: list[str]) -> dict[str, str]:
    from deep_translator import GoogleTranslator

    cache = load_cache(lang)
    todo = [g for g in all_unique if g not in cache]
    if not todo:
        print(f"  {lang}: all {len(all_unique)} entries already cached")
        return cache

    print(f"  {lang}: {len(todo)} to translate (cached: {len(cache)})")
    t = GoogleTranslator(source="en", target=lang)
    total = len(todo)
    for i in range(0, total, BATCH_SIZE):
        batch = todo[i : i + BATCH_SIZE]
        # Use a delimiter that Google preserves cleanly
        joined = "\n".join(batch)
        try:
            result = t.translate(joined)
            parts = result.split("\n")
            if len(parts) != len(batch):
                # Fall back to per-line translation for this batch
                print(f"    batch {i//BATCH_SIZE+1}: line count mismatch, falling back")
                parts = []
                for line in batch:
                    try:
                        parts.append(t.translate(line))
                    except Exception:
                        parts.append(line)
                    time.sleep(0.1)
            for src, dst in zip(batch, parts):
                cache[src] = dst.strip()
        except Exception as e:
            print(f"    batch {i//BATCH_SIZE+1}: {e!r} — keeping originals")
            for src in batch:
                cache[src] = src

        # Persist progress every batch
        save_cache(lang, cache)
        done = min(i + BATCH_SIZE, total)
        if (i // BATCH_SIZE) % 10 == 0:
            pct = 100 * done / total
            print(f"    {done}/{total} ({pct:.1f}%) cached")
        time.sleep(DELAY_BETWEEN_BATCHES)
    return cache


def build_strongs_tables(lang: str, en_map: dict[str, str], en2lang: dict[str, str]) -> None:
    out_dir = GLOSS_DIR / lang
    out_dir.mkdir(parents=True, exist_ok=True)
    he_table: dict[str, str] = {}
    grc_table: dict[str, str] = {}
    for sn, eng in en_map.items():
        translated = en2lang.get(eng, eng)
        if sn.startswith("H"):
            he_table[sn] = translated
        elif sn.startswith("G"):
            grc_table[sn] = translated
    (out_dir / "he.json").write_text(json.dumps(he_table, ensure_ascii=False, separators=(",", ":")))
    (out_dir / "grc.json").write_text(json.dumps(grc_table, ensure_ascii=False, separators=(",", ":")))
    print(f"  {lang}: he.json ({len(he_table)} entries), grc.json ({len(grc_table)} entries)")


def main() -> None:
    en_he = json.loads(EN_HE.read_text())
    en_grc = json.loads(EN_GRC.read_text())
    en_combined: dict[str, str] = {**en_he, **en_grc}

    # Mirror the en sources into glosses/en/{he,grc}.json for symmetry
    en_dir = GLOSS_DIR / "en"
    en_dir.mkdir(parents=True, exist_ok=True)
    (en_dir / "he.json").write_text(json.dumps(en_he, ensure_ascii=False, separators=(",", ":")))
    (en_dir / "grc.json").write_text(json.dumps(en_grc, ensure_ascii=False, separators=(",", ":")))

    unique = collect_unique_glosses(en_combined)
    print(f"Total Strong's entries: {len(en_combined)} · Unique English glosses: {len(unique)}")

    for lang in LANGS:
        print(f"\n→ Translating to {lang}…")
        cache = translate_missing(lang, unique)
        print(f"  building Strong's tables for {lang}…")
        build_strongs_tables(lang, en_combined, cache)


if __name__ == "__main__":
    main()
