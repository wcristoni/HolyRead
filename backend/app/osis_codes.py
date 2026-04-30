"""OSIS book codes for the 66 books, 0-indexed canonical order matching frontend.

OT (0..38) uses morphhb's WLC filenames. NT (39..65) uses MorphGNT/SBLGNT codes.
"""

OT_OSIS = [
    "Gen", "Exod", "Lev", "Num", "Deut",
    "Josh", "Judg", "Ruth",
    "1Sam", "2Sam", "1Kgs", "2Kgs",
    "1Chr", "2Chr", "Ezra", "Neh", "Esth",
    "Job", "Ps", "Prov", "Eccl", "Song",
    "Isa", "Jer", "Lam", "Ezek", "Dan",
    "Hos", "Joel", "Amos", "Obad", "Jonah",
    "Mic", "Nah", "Hab", "Zeph", "Hag", "Zech", "Mal",
]

NT_OSIS = [
    "Matt", "Mark", "Luke", "John",
    "Acts",
    "Rom", "1Cor", "2Cor", "Gal", "Eph", "Phil", "Col",
    "1Thess", "2Thess", "1Tim", "2Tim", "Titus", "Phlm",
    "Heb", "Jas", "1Pet", "2Pet", "1John", "2John", "3John", "Jude", "Rev",
]

ALL_OSIS = OT_OSIS + NT_OSIS

OSIS_TO_INDEX = {code: i for i, code in enumerate(ALL_OSIS)}

# MorphGNT filename prefixes use Bible-wide numbering (40..66 for NT).
NT_FILE_PREFIX = {
    39: "61-Mt",
    40: "62-Mk",
    41: "63-Lk",
    42: "64-Jn",
    43: "65-Ac",
    44: "66-Ro",
    45: "67-1Co",
    46: "68-2Co",
    47: "69-Ga",
    48: "70-Eph",
    49: "71-Php",
    50: "72-Col",
    51: "73-1Th",
    52: "74-2Th",
    53: "75-1Ti",
    54: "76-2Ti",
    55: "77-Tit",
    56: "78-Phm",
    57: "79-Heb",
    58: "80-Jas",
    59: "81-1Pe",
    60: "82-2Pe",
    61: "83-1Jn",
    62: "84-2Jn",
    63: "85-3Jn",
    64: "86-Jud",
    65: "87-Re",
}
