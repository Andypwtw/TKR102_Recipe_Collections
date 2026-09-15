from __future__ import annotations
import re
from fractions import Fraction

UNIT_ALIASES = {
    "公克": "g", "克": "g", "g": "g",
    "公斤": "kg", "kg": "kg",
    "毫升": "ml", "ml": "ml",
    "公升": "l", "L": "l", "l": "l",
    "大匙": "tbsp", "湯匙": "tbsp",
    "小匙": "tsp", "茶匙": "tsp",
    "斤": "jin",
}

MASS_TO_G = {"g": 1.0, "kg": 1000.0, "jin": 600.0}
VOLUME_TO_ML = {"ml": 1.0, "l": 1000.0, "tbsp": 15.0, "tsp": 5.0}

def clean_text(value: str) -> str:
    value = str(value or "")
    value = value.replace("\u3000", " ").replace("｜", "|")
    value = re.sub(r"\s+", " ", value).strip()
    return value

def parse_number(text: str):
    text = str(text or "").strip()
    if not text:
        return None
    try:
        if "/" in text and re.fullmatch(r"\d+\s*/\s*\d+", text):
            return float(Fraction(text.replace(" ", "")))
        return float(text)
    except Exception:
        return None

def normalize_unit(unit: str) -> str:
    u = clean_text(unit)
    return UNIT_ALIASES.get(u, u)

def direct_weight_g(quantity, unit):
    if quantity is None:
        return None
    u = normalize_unit(unit)
    if u in MASS_TO_G:
        return float(quantity) * MASS_TO_G[u]
    return None
