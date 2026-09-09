from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional


QUALITATIVE_WORDS = ("適量", "少許", "隨意", "酌量", "酌情", "數滴")

UNIT_ALIASES = {
    "公克": "g", "公": "g", "克": "g", "g": "g", "G": "g",
    "公斤": "kg", "kg": "kg", "KG": "kg",
    "斤": "斤", "兩": "兩", "钱": "錢", "錢": "錢",
    "毫升": "ml", "ml": "ml", "mL": "ml", "ML": "ml",
    "㏄": "cc", "cc": "cc", "CC": "cc", "c.c.": "cc",
    "公升": "L", "l": "L", "L": "L",
    "杯": "杯", "大匙": "大匙", "湯匙": "大匙",
    "小匙": "小匙", "茶匙": "茶匙",
    "顆": "顆", "個": "個", "个": "個", "條": "條", "条": "條",
    "片": "片", "塊": "塊", "块": "塊", "朵": "朵", "支": "支",
    "瓣": "瓣", "粒": "粒", "根": "根", "把": "把", "包": "包",
    "盒": "盒", "罐": "罐", "張": "張", "张": "張", "滴": "滴",
    "隻": "隻", "只": "隻", "尾": "尾", "葉": "葉", "格": "格",
    "碗": "碗", "匙": "匙", "份": "份", "枝": "枝", "株": "株",
    "棵": "棵", "瓶": "瓶", "段": "段", "球": "球",
}

VOLUME_TO_ML = {
    "ml": 1.0,
    "cc": 1.0,
    "L": 1000.0,
    "杯": 240.0,
    "大匙": 15.0,
    "小匙": 5.0,
    "茶匙": 5.0,
}

MASS_TO_GRAMS = {
    "g": 1.0,
    "kg": 1000.0,
    "斤": 600.0,   # 台灣市斤
    "兩": 37.5,    # 台灣市兩
    "錢": 3.75,
}

CHINESE_DIGITS = {
    "零": 0, "〇": 0, "一": 1, "二": 2, "兩": 2, "两": 2, "三": 3,
    "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9,
}


@dataclass
class ParsedIngredient:
    raw_text: str
    raw_name: str
    canonical_name: str
    raw_amount_text: str
    quantity_min: Optional[float]
    quantity_max: Optional[float]
    quantity_value: Optional[float]
    canonical_unit: Optional[str]
    weight_g: Optional[float]
    is_estimated: bool
    needs_manual_review: bool
    review_reason: Optional[str]

    def to_dict(self) -> dict:
        return asdict(self)


def normalize_text(value: object) -> str:
    if value is None:
        return ""
    text = unicodedata.normalize("NFKC", str(value))
    text = text.replace("∼", "~").replace("～", "~").replace("－", "-")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def clean_ingredient_name(name: str) -> str:
    name = normalize_text(name)
    name = re.sub(r"^\s*(?:材料)?[A-Za-z]?\d+\s*[.、:：]\s*", "", name)
    name = re.sub(r"^[A-Za-z]\s*[.、:：]\s*", "", name)
    name = re.sub(r"\s*\([^)]*\)\s*$", "", name)
    return name.strip(" -、,，;；")


def load_alias_map(path: Path) -> dict[str, str]:
    aliases: dict[str, str] = {}
    if not path.exists():
        return aliases
    rows = json.loads(path.read_text(encoding="utf-8"))
    for row in rows:
        alias = clean_ingredient_name(row.get("alias", ""))
        canonical = clean_ingredient_name(row.get("canonical", ""))
        if alias and canonical:
            aliases[alias] = canonical
    return aliases


def standardize_ingredient_name(name: str, aliases: dict[str, str]) -> str:
    cleaned = clean_ingredient_name(name)
    return aliases.get(cleaned, cleaned)


def chinese_integer_to_number(text: str) -> Optional[float]:
    text = text.strip()
    if not text:
        return None
    if text in CHINESE_DIGITS:
        return float(CHINESE_DIGITS[text])
    if text == "十":
        return 10.0
    if "十" in text:
        left, _, right = text.partition("十")
        tens = CHINESE_DIGITS.get(left, 1) if left else 1
        ones = CHINESE_DIGITS.get(right, 0) if right else 0
        return float(tens * 10 + ones)
    return None


def parse_single_number(token: str) -> Optional[float]:
    token = normalize_text(token).replace(" ", "")
    if not token:
        return None
    if token == "半":
        return 0.5

    mixed = re.fullmatch(r"(\d+(?:\.\d+)?)又(\d+)\/(\d+)", token)
    if mixed:
        whole, num, den = mixed.groups()
        return float(whole) + float(num) / float(den)

    frac = re.fullmatch(r"(\d+)\/(\d+)", token)
    if frac:
        num, den = frac.groups()
        den_value = float(den)
        return float(num) / den_value if den_value else None

    try:
        return float(token)
    except ValueError:
        return chinese_integer_to_number(token)


def split_range_token(token: str) -> tuple[Optional[float], Optional[float], bool]:
    token = normalize_text(token).replace(" ", "")
    if not token:
        return None, None, False
    for sep in ("~", "-"):
        if sep in token:
            left, right = token.split(sep, 1)
            low = parse_single_number(left)
            high = parse_single_number(right)
            if low is not None and high is not None:
                return min(low, high), max(low, high), True
    value = parse_single_number(token)
    return value, value, False


def load_unit_weight_map(path: Path) -> dict[tuple[str, str], float]:
    result: dict[tuple[str, str], float] = {}
    if not path.exists():
        return result
    rows = json.loads(path.read_text(encoding="utf-8"))
    for row in rows:
        ingredient = clean_ingredient_name(row.get("ingredient", ""))
        unit = normalize_text(row.get("unit", ""))
        grams = row.get("grams_per_unit")
        if not ingredient or not unit or grams in (None, ""):
            continue
        try:
            result[(ingredient, UNIT_ALIASES.get(unit, unit))] = float(grams)
        except (TypeError, ValueError):
            continue
    return result




def load_density_map(path: Path) -> dict[str, float]:
    """Load ACTIVE ingredient density rows (g/ml) used for volume-to-weight conversion."""
    result: dict[str, float] = {}
    if not path.exists():
        return result
    rows = json.loads(path.read_text(encoding="utf-8"))
    for row in rows:
        ingredient = clean_ingredient_name(row.get("ingredient", ""))
        density = row.get("density_g_ml")
        status = normalize_text(row.get("status", "ACTIVE")).upper() or "ACTIVE"
        if not ingredient or density in (None, "") or status != "ACTIVE":
            continue
        try:
            result[ingredient] = float(density)
        except (TypeError, ValueError):
            continue
    return result


def split_name_and_amount(raw_text: str) -> tuple[str, str]:
    text = normalize_text(raw_text)
    text = re.sub(r"^\s*(?:材料)?[A-Za-z]?\d+\s*[.、:：]\s*", "", text)
    parts = text.split(" ", 1)
    if len(parts) == 1:
        return clean_ingredient_name(parts[0]), ""
    return clean_ingredient_name(parts[0]), parts[1].strip()


def _find_unit(amount_text: str) -> tuple[Optional[str], str]:
    amount = normalize_text(amount_text)
    candidates = sorted(UNIT_ALIASES.keys(), key=len, reverse=True)
    for alias in candidates:
        match = re.search(re.escape(alias), amount, flags=re.IGNORECASE)
        if match:
            return UNIT_ALIASES[alias], amount[: match.start()].strip()
    return None, amount


def parse_amount(amount_text: str) -> dict:
    raw = normalize_text(amount_text)
    if not raw:
        return {
            "quantity_min": None,
            "quantity_max": None,
            "quantity_value": None,
            "canonical_unit": None,
            "is_estimated": False,
            "qualitative": False,
            "reason": "缺少數量/單位",
        }

    approximate = bool(re.search(r"約|大約|左右|約莫", raw))
    for word in QUALITATIVE_WORDS:
        if word in raw:
            unit = "少許" if word == "數滴" else word
            return {
                "quantity_min": None,
                "quantity_max": None,
                "quantity_value": None,
                "canonical_unit": unit if unit in {"適量", "少許", "隨意", "酌量"} else "適量/少許",
                "is_estimated": True,
                "qualitative": True,
                "reason": f"定性用量：{word}",
            }

    unit, before_unit = _find_unit(raw)
    before_unit = re.sub(r"約|大約|左右|約莫", "", before_unit)
    before_unit = re.sub(r"\([^)]*\)", "", before_unit).strip()

    # 保留最接近單位的數字區段，例如「1又1/2」或「2~3」。
    number_match = re.search(
        r"(\d+(?:\.\d+)?又\d+/\d+|\d+/\d+|\d+(?:\.\d+)?(?:[~-]\d+(?:\.\d+)?)?|半|[一二三四五六七八九十兩两]+)$",
        before_unit,
    )
    token = number_match.group(1) if number_match else ""
    qmin, qmax, is_range = split_range_token(token)
    qvalue = None if qmin is None else ((qmin + qmax) / 2 if qmax is not None else qmin)

    reason = None
    if qvalue is None:
        reason = "無法解析數量"
    elif unit is None:
        reason = "無法辨識單位"

    return {
        "quantity_min": qmin,
        "quantity_max": qmax,
        "quantity_value": qvalue,
        "canonical_unit": unit,
        "is_estimated": approximate or is_range,
        "qualitative": False,
        "reason": reason,
    }


def calculate_weight_g(
    canonical_name: str,
    quantity_value: Optional[float],
    unit: Optional[str],
    unit_weights: dict[tuple[str, str], float],
    densities: Optional[dict[str, float]] = None,
) -> tuple[Optional[float], bool, Optional[str]]:
    if quantity_value is None or unit is None:
        return None, False, None

    if unit in MASS_TO_GRAMS:
        return quantity_value * MASS_TO_GRAMS[unit], False, None

    grams_per_unit = unit_weights.get((canonical_name, unit))
    if grams_per_unit is not None:
        return quantity_value * grams_per_unit, True, None

    if unit in VOLUME_TO_ML:
        density = (densities or {}).get(canonical_name)
        if density is not None:
            volume_ml = quantity_value * VOLUME_TO_ML[unit]
            return volume_ml * density, True, None
        return None, False, f"{canonical_name} 缺少 density_g_ml，無法將 {unit} 轉為克"

    return None, False, f"{unit} 需要食材專屬重量換算"


def parse_ingredient_line(
    raw_text: str,
    aliases: dict[str, str],
    unit_weights: dict[tuple[str, str], float],
    densities: Optional[dict[str, float]] = None,
) -> ParsedIngredient:
    raw_name, raw_amount = split_name_and_amount(raw_text)
    canonical_name = standardize_ingredient_name(raw_name, aliases)
    parsed = parse_amount(raw_amount)
    weight_g, weight_is_estimated, weight_reason = calculate_weight_g(
        canonical_name,
        parsed["quantity_value"],
        parsed["canonical_unit"],
        unit_weights,
        densities,
    )

    reasons = [x for x in (parsed["reason"], weight_reason) if x]
    needs_review = bool(parsed["qualitative"] or reasons)

    return ParsedIngredient(
        raw_text=normalize_text(raw_text),
        raw_name=raw_name,
        canonical_name=canonical_name or "未命名食材",
        raw_amount_text=raw_amount,
        quantity_min=parsed["quantity_min"],
        quantity_max=parsed["quantity_max"],
        quantity_value=parsed["quantity_value"],
        canonical_unit=parsed["canonical_unit"],
        weight_g=weight_g,
        is_estimated=bool(parsed["is_estimated"] or weight_is_estimated),
        needs_manual_review=needs_review,
        review_reason="；".join(reasons) if reasons else None,
    )
