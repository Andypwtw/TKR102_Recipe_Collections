from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

import sys

PYTHON_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = PYTHON_DIR.parent
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))

from app.services.normalization import normalize_text


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Profile raw YTower recipe JSON.")
    parser.add_argument("--input", type=Path, default=PROJECT_ROOT / "data" / "raw" / "ytower_seq_recipes.json")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "data" / "processed" / "profile_report.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    with args.input.open("r", encoding="utf-8") as f:
        rows = json.load(f)

    keys = Counter()
    seq_counter = Counter()
    recipe_name_counter = Counter()
    keyword_counter = Counter()
    ingredient_lines = 0
    qualitative_counter = Counter()
    suffix_counter = Counter()

    for row in rows:
        keys.update(row.keys())
        seq = normalize_text(row.get("SEQ"))
        name = normalize_text(row.get("食譜名稱"))
        if seq:
            seq_counter[seq] += 1
        if name:
            recipe_name_counter[name] += 1
        for keyword in normalize_text(row.get("關鍵字")).split(","):
            keyword = keyword.strip()
            if keyword:
                keyword_counter[keyword] += 1
        materials = normalize_text(row.get("材料"))
        for item in materials.split("|"):
            item = item.strip()
            if not item:
                continue
            ingredient_lines += 1
            for word in ("適量", "少許", "隨意", "酌量", "數滴"):
                if word in item:
                    qualitative_counter[word] += 1
            m = re.search(r"([\u4e00-\u9fffA-Za-z.]+)\s*(?:\([^)]*\))?$", item)
            if m:
                suffix_counter[m.group(1)] += 1

    report = {
        "recipe_count": len(rows),
        "observed_keys": dict(keys),
        "duplicate_seq_count": sum(1 for count in seq_counter.values() if count > 1),
        "duplicate_recipe_name_count": sum(1 for count in recipe_name_counter.values() if count > 1),
        "ingredient_line_count": ingredient_lines,
        "top_keywords": keyword_counter.most_common(30),
        "qualitative_amounts": dict(qualitative_counter),
        "top_amount_suffixes": suffix_counter.most_common(50),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
