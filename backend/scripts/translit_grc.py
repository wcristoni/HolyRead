"""Greek transliteration — Erasmian and Modern variants.

Erasmian = academic/SBL convention (η→ē, ω→ō, θ→th, φ→ph, χ→ch, υ→y, etc).
Modern   = iotacism applied (η/ι/υ/ει/οι/υι→i, β→v, γ→gh, δ→dh, χ→kh, θ→th).

Diacritics are stripped after a rough breathings check (rough = leading "h").
"""
from __future__ import annotations

import unicodedata


def _has_rough(c: str) -> bool:
    """Detect a rough breathing on this composed character."""
    decomp = unicodedata.normalize("NFD", c)
    return "̔" in decomp  # combining reversed comma above


def _base(c: str) -> str:
    """Strip diacritics → base letter."""
    return "".join(
        ch for ch in unicodedata.normalize("NFD", c)
        if unicodedata.category(ch) != "Mn"
    )


# Single letters → Erasmian
ERAS = {
    "α": "a", "β": "b", "γ": "g", "δ": "d", "ε": "e",
    "ζ": "z", "η": "ē", "θ": "th", "ι": "i", "κ": "k",
    "λ": "l", "μ": "m", "ν": "n", "ξ": "x", "ο": "o",
    "π": "p", "ρ": "r", "σ": "s", "ς": "s", "τ": "t",
    "υ": "y", "φ": "ph", "χ": "ch", "ψ": "ps", "ω": "ō",
}

# Modern Greek (basic)
MOD_SINGLE = {
    "α": "a", "β": "v", "γ": "gh", "δ": "dh", "ε": "e",
    "ζ": "z", "η": "i", "θ": "th", "ι": "i", "κ": "k",
    "λ": "l", "μ": "m", "ν": "n", "ξ": "ks", "ο": "o",
    "π": "p", "ρ": "r", "σ": "s", "ς": "s", "τ": "t",
    "υ": "i", "φ": "f", "χ": "kh", "ψ": "ps", "ω": "o",
}

# Digraphs / context rules for Modern
MOD_DIGRAPHS = {
    "αι": "e",  "ει": "i", "οι": "i", "υι": "i",
    "ου": "u",
    "αυ": "av", "ευ": "ev", "ηυ": "iv",
}

# γγ → ng, γκ → ng, γξ → ngz, γχ → nkh (Modern); Erasmian leaves them
MOD_GAMMA_NASAL = {"γγ": "ng", "γκ": "ng", "γξ": "ngz", "γχ": "nkh"}


def _apply_rough(word_lower: str, rough_idx: int, out: list[str]) -> None:
    if rough_idx == 0:
        out.append("h")


ERAS_DIGRAPHS = {
    "ου": "ou", "ευ": "eu", "αυ": "au", "ηυ": "ēu",
    "ει": "ei", "οι": "oi", "αι": "ai", "υι": "ui",
}
ERAS_GAMMA_NASAL = {"γγ": "ng", "γκ": "nk", "γξ": "nx", "γχ": "nch"}


def transliterate_eras(word: str) -> str:
    if not word:
        return ""
    word_lower = word.lower()
    # Detect rough breathing on the first vowel
    rough_first = False
    for ch in word_lower:
        if _base(ch) and _has_rough(ch):
            rough_first = True
            break
    base = "".join(_base(c) for c in word_lower if _base(c))
    for k, v in ERAS_GAMMA_NASAL.items():
        base = base.replace(k, v)
    for k, v in ERAS_DIGRAPHS.items():
        base = base.replace(k, v)
    out = []
    for ch in base:
        if "a" <= ch <= "z" or ch in "āēīōū":
            out.append(ch)
        else:
            out.append(ERAS.get(ch, ch))
    s = "".join(out)
    return ("h" + s) if rough_first else s


def transliterate_mod(word: str) -> str:
    if not word:
        return ""
    word_lower = word.lower()
    # Strip diacritics down to base letters first (Modern doesn't honour breathings)
    base = "".join(_base(c) for c in word_lower if _base(c))
    # Apply gamma-nasal digraphs
    for k, v in MOD_GAMMA_NASAL.items():
        base = base.replace(k, v)
    # Apply vowel digraphs
    for k, v in MOD_DIGRAPHS.items():
        base = base.replace(k, v)
    # Now map remaining single letters
    out = []
    i = 0
    while i < len(base):
        ch = base[i]
        # Skip our already-translated ASCII (lowercase a-z)
        if "a" <= ch <= "z":
            out.append(ch)
            i += 1
            continue
        out.append(MOD_SINGLE.get(ch, ch))
        i += 1
    return "".join(out)
