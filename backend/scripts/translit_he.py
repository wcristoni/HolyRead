"""Deterministic Hebrew transliteration (light SBL-style).

Rules are kept simple — they are enough to give a learner a phonetic anchor.
Cantillation marks (te'amim) are stripped. Niqqud (vowels) drives the vowel
rendering. We follow the SBL Handbook simplified scheme:

  shewa (ְ) → "" (silent) when at end of syllable, "ə" when vocal — without
  full syllabification we approximate as "ə" except at word end.
  patach/qamats → a (long qamats also a — quality, not quantity)
  segol/tsere → e
  hiriq → i
  holam/qamats-hatuf → o
  shuruq/qibbuts → u
  hatef vowels → short variants (ă, ĕ, ŏ)

Final letter forms are normalised. Dagesh is preserved by doubling (light
treatment for begadkefat is omitted to keep the output readable).
"""
from __future__ import annotations

# Cantillation block range
_CANT_RE_RANGES = (
    (0x0591, 0x05AF),  # te'amim
    (0x05BD, 0x05BD),  # meteg (kept as 0x05BD outside range, drop too)
    (0x05BF, 0x05BF),  # rafe
    (0x05C0, 0x05C0),
    (0x05C3, 0x05C3),
    (0x05C6, 0x05C6),
    (0x05F3, 0x05F4),
)

CONS = {
    "א": "ʾ", "ב": "v", "ג": "g", "ד": "d", "ה": "h",
    "ו": "v", "ז": "z", "ח": "ḥ", "ט": "ṭ", "י": "y",
    "כ": "kh", "ך": "kh", "ל": "l", "מ": "m", "ם": "m",
    "נ": "n", "ן": "n", "ס": "s", "ע": "ʿ", "פ": "f",
    "ף": "f", "צ": "ts", "ץ": "ts", "ק": "q", "ר": "r",
    "שׁ": "sh", "שׂ": "s", "ש": "sh",  # default to sh if no dot
    "ת": "t",
}

# When a consonant has dagesh, begadkefat shifts (light approximation):
DAGESH_BEGADKEFAT = {"ב": "b", "כ": "k", "פ": "p", "ך": "k", "ף": "p"}

# Niqqud marks
NIQQUD = {
    "ַ": "a",  # patach
    "ָ": "a",  # qamats
    "ֶ": "e",  # segol
    "ֵ": "e",  # tsere
    "ִ": "i",  # hiriq
    "ֹ": "o",  # holam
    "ֻ": "u",  # qibbuts
    "ְ": "ə",  # shewa (treat as schwa)
    "ֲ": "ă",
    "ֱ": "ĕ",
    "ֳ": "ŏ",
}

DAGESH = "ּ"
SHIN_DOT = "ׁ"
SIN_DOT = "ׂ"
SHUREQ_VAV = "וּ"  # ו + dagesh = shureq when no other vowel


def _is_cant(cp: int) -> bool:
    for lo, hi in _CANT_RE_RANGES:
        if lo <= cp <= hi:
            return True
    return False


def strip_cantillation(text: str) -> str:
    return "".join(c for c in text if not _is_cant(ord(c)))


def transliterate(word: str) -> str:
    """Transliterate a single Hebrew word (with niqqud, may have / boundaries)."""
    if not word:
        return ""
    # Drop morpheme separator slashes from morphhb
    word = word.replace("/", "")
    word = strip_cantillation(word)
    out: list[str] = []
    i = 0
    n = len(word)
    while i < n:
        ch = word[i]
        # Shin/sin with dot
        if ch == "ש" and i + 1 < n and word[i + 1] in (SHIN_DOT, SIN_DOT):
            out.append("sh" if word[i + 1] == SHIN_DOT else "s")
            i += 2
            continue
        # Vav-shureq (ו with dagesh, no vowel)
        if ch == "ו" and i + 1 < n and word[i + 1] == DAGESH:
            out.append("u")
            i += 2
            continue
        # Begadkefat shift on dagesh
        if ch in DAGESH_BEGADKEFAT and i + 1 < n and word[i + 1] == DAGESH:
            out.append(DAGESH_BEGADKEFAT[ch])
            i += 2
            continue
        # Plain consonant
        if ch in CONS:
            out.append(CONS[ch])
            i += 1
            continue
        # Niqqud
        if ch in NIQQUD:
            v = NIQQUD[ch]
            # silent shewa at end of word
            if v == "ə" and i == n - 1:
                i += 1
                continue
            out.append(v)
            i += 1
            continue
        # Drop any leftover marks (dagesh w/o begadkefat consonant, etc.)
        if ord(ch) >= 0x0591 and ord(ch) <= 0x05C7:
            i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)
