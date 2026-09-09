from __future__ import annotations

import argparse
import json
import re
import statistics
import unicodedata
from collections import defaultdict
from pathlib import Path

import sys

PYTHON_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = PYTHON_DIR.parent
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))

from app.services.normalization import load_alias_map, standardize_ingredient_name

MASS_TO_GRAMS = {
    "g": 1.0,
    "克": 1.0,
    "公克": 1.0,
    "kg": 1000.0,
    "公斤": 1000.0,
    "斤": 600.0,
    "兩": 37.5,
    "錢": 3.75,
}
COUNT_UNITS = "隻|尾|葉|片|條|個|顆|塊|朵|支|瓣|粒|根|把|包|盒|罐|張|格|杯"
NUMBER = r"(?:\d+(?:\.\d+)?(?:又\d+/\d+)?|\d+/\d+|半)"


def parse_number(value: str) -> float | None:
    value = value.strip()
    if value == "半":
        return 0.5
    m = re.fullmatch(r"(\d+(?:\.\d+)?)又(\d+)/(\d+)", value)
    if m:
        return float(m.group(1)) + float(m.group(2)) / float(m.group(3))
    m = re.fullmatch(r"(\d+)/(\d+)", value)
    if m:
        den = float(m.group(2))
        return float(m.group(1)) / den if den else None
    try:
        return float(value)
    except ValueError:
        return None


def clean_text(value: str) -> str:
    return unicodedata.normalize("NFKC", value).replace("∼", "~").replace("～", "~")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build ingredient+unit grams_per_unit from explicit YTower equivalences.")
    parser.add_argument("--input", type=Path, default=PROJECT_ROOT / "data" / "raw" / "ytower_seq_recipes.json")
    parser.add_argument("--aliases", type=Path, default=PROJECT_ROOT / "data" / "reference" / "ingredient_aliases.json")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "data" / "reference" / "unit_weight_map.json")
    parser.add_argument("--candidates", type=Path, default=PROJECT_ROOT / "data" / "reference" / "unit_weight_candidates.json")
    args = parser.parse_args()

    aliases = load_alias_map(args.aliases)
    recipes = json.loads(args.input.read_text(encoding="utf-8"))
    observations: dict[tuple[str, str], list[tuple[float, str]]] = defaultdict(list)

    # Pattern A: ingredient 1條(約600公克)
    direct = re.compile(
        rf"^(.*?)\s+({NUMBER})\s*({COUNT_UNITS})\s*[\(（](.*?)[\)）]",
        re.I,
    )
    # Pattern B: ingredient 600公克(1條)
    reverse = re.compile(
        rf"^(.*?)\s+({NUMBER})\s*(公斤|kg|公克|克|g|斤|兩|錢)\s*[\(（](.*?)[\)）]",
        re.I,
    )
    mass_inside = re.compile(
        rf"(?:約|共)?\s*({NUMBER})(?:\s*[~\-]\s*({NUMBER}))?\s*(公斤|kg|公克|克|g|斤|兩|錢)",
        re.I,
    )
    count_inside = re.compile(
        rf"(?:約|或)?\s*({NUMBER})(?:\s*[~\-]\s*({NUMBER}))?\s*({COUNT_UNITS})",
        re.I,
    )

    for recipe in recipes:
        for raw in [x.strip() for x in recipe.get("材料", "").split("|") if x.strip()]:
            text = clean_text(raw)
            m = direct.match(text)
            if m:
                raw_name, qty_text, unit, inside = m.groups()
                qty = parse_number(qty_text)
                mm = mass_inside.search(inside)
                if qty and mm:
                    a, b, mass_unit = mm.groups()
                    q1 = parse_number(a)
                    q2 = parse_number(b) if b else q1
                    if q1 is not None and q2 is not None:
                        mass_qty = (q1 + q2) / 2
                        factor = MASS_TO_GRAMS[mass_unit.lower() if mass_unit.lower() == "kg" else mass_unit]
                        name = standardize_ingredient_name(raw_name, aliases)
                        observations[(name, unit)].append((mass_qty * factor / qty, raw))
                continue

            m = reverse.match(text)
            if not m:
                continue
            raw_name, mass_qty_text, mass_unit, inside = m.groups()
            if "作" in inside:
                continue
            cm = count_inside.search(inside)
            mass_qty = parse_number(mass_qty_text)
            if not cm or mass_qty is None:
                continue
            a, b, unit = cm.groups()
            q1 = parse_number(a)
            q2 = parse_number(b) if b else q1
            if q1 is None or q2 is None:
                continue
            count = (q1 + q2) / 2
            if not count:
                continue
            factor = MASS_TO_GRAMS[mass_unit.lower() if mass_unit.lower() == "kg" else mass_unit]
            name = standardize_ingredient_name(raw_name, aliases)
            observations[(name, unit)].append((mass_qty * factor / count, raw))

    fields = [
        "ingredient", "unit", "grams_per_unit", "sample_count", "min_g", "max_g",
        "variation_ratio", "confidence", "status", "source", "examples", "note",
    ]
    candidates = []
    active = []
    for (ingredient, unit), values in sorted(observations.items()):
        grams = [x[0] for x in values]
        median_g = statistics.median(grams)
        ratio = max(grams) / min(grams) if min(grams) else 999
        confidence = "高" if len(grams) >= 2 and ratio <= 1.15 else ("中" if ratio <= 1.5 else "低")
        status = "ACTIVE" if ratio <= 1.5 else "REVIEW"
        row = {
            "ingredient": ingredient,
            "unit": unit,
            "grams_per_unit": round(median_g, 3),
            "sample_count": len(grams),
            "min_g": round(min(grams), 3),
            "max_g": round(max(grams), 3),
            "variation_ratio": round(ratio, 3),
            "confidence": confidence,
            "status": status,
            "source": "ytower_json_explicit_equivalence",
            "examples": " / ".join(x[1] for x in values[:3]),
            "note": "由來源 JSON 中的明示重量/數量對照換算；使用時視為估算重量。",
        }
        candidates.append(row)
        if status == "ACTIVE":
            active.append(row)

    for path, rows in ((args.output, active), (args.candidates, candidates)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"candidate mappings: {len(candidates)}")
    print(f"active mappings: {len(active)}")
    print(f"review mappings: {len(candidates) - len(active)}")
    print(f"output: {args.output}")


if __name__ == "__main__":
    main()
