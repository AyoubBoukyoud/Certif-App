"""Formula normalisation for locale-independent matching.

Excel stores formulas in the file with English function names and comma
separators regardless of the UI language, but content authors may write
patterns using French names. ``normalize`` maps everything to a canonical
uppercase English form so patterns match either way.
"""
from __future__ import annotations

import re

# French display name -> canonical English function name.
FR_TO_EN = {
    "MOYENNE.SI.ENS": "AVERAGEIFS",
    "MOYENNE.SI": "AVERAGEIF",
    "MOYENNE": "AVERAGE",
    "NB.SI.ENS": "COUNTIFS",
    "NB.SI": "COUNTIF",
    "NB.VAL": "COUNTA",
    "NBVAL": "COUNTA",
    "NB": "COUNT",
    "SOMME.SI.ENS": "SUMIFS",
    "SOMME.SI": "SUMIF",
    "SOMME": "SUM",
    "SI.CONDITIONS": "IFS",
    "SI": "IF",
    "CONCATENER": "CONCATENATE",
    "CONCAT": "CONCAT",
    "MAJUSCULE": "UPPER",
    "MINUSCULE": "LOWER",
    "NOMPROPRE": "PROPER",
    "GAUCHE": "LEFT",
    "DROITE": "RIGHT",
    "STXT": "MID",
    "MAX": "MAX",
    "MIN": "MIN",
    "RECHERCHEV": "VLOOKUP",
    "RECHERCHEX": "XLOOKUP",
    "AUJOURDHUI": "TODAY",
    "MAINTENANT": "NOW",
}

# Longest names first so e.g. SOMME.SI is replaced before SOMME.
_ORDERED = sorted(FR_TO_EN.items(), key=lambda kv: -len(kv[0]))


def normalize(formula: str | None) -> str:
    if not formula:
        return ""
    f = str(formula)
    if f.startswith("="):
        f = f[1:]
    f = f.upper()
    for fr, en in _ORDERED:
        f = re.sub(rf"\b{re.escape(fr)}\b", en, f)
    # French argument separator -> English.
    f = f.replace(";", ",")
    # Collapse whitespace.
    f = re.sub(r"\s+", "", f)
    return f
