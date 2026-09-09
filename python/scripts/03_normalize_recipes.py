from __future__ import annotations

import argparse
import json
from pathlib import Path

import sys

PYTHON_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = PYTHON_DIR.parent
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))

from app.services.normalization import (
    load_alias_map,
    load_density_map,
    load_unit_weight_map,
    parse_ingredient_line,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize ingredient names, amounts and units.")
    parser.add_argument("--input", type=Path, default=PROJECT_ROOT / "data" / "processed" / "recipes_clean.json")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "data" / "processed" / "recipes_normalized.json")
    parser.add_argument("--aliases", type=Path, default=PROJECT_ROOT / "data" / "reference" / "ingredient_aliases.json")
    parser.add_argument("--unit-weights", type=Path, default=PROJECT_ROOT / "data" / "reference" / "unit_weight_map.json")
    parser.add_argument("--densities", type=Path, default=PROJECT_ROOT / "data" / "reference" / "ingredient_density_map.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    aliases = load_alias_map(args.aliases)
    unit_weights = load_unit_weight_map(args.unit_weights)
    densities = load_density_map(args.densities)
    args.output.parent.mkdir(parents=True, exist_ok=True)

    recipes = 0
    ingredient_rows = 0
    review_rows = 0
    known_weight_rows = 0

    source_recipes = json.loads(args.input.read_text(encoding="utf-8"))
    normalized_recipes = []
    for recipe in source_recipes:
        normalized_materials = []
        for material in recipe.get("materials", []):
            parsed = parse_ingredient_line(material["raw_text"], aliases, unit_weights, densities).to_dict()
            parsed["line_no"] = material["line_no"]
            normalized_materials.append(parsed)
            ingredient_rows += 1
            review_rows += int(parsed["needs_manual_review"])
            known_weight_rows += int(parsed["weight_g"] is not None)
        recipe["materials"] = normalized_materials
        normalized_recipes.append(recipe)
        recipes += 1

    args.output.write_text(
        json.dumps(normalized_recipes, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"recipes: {recipes}")
    print(f"ingredient rows: {ingredient_rows}")
    print(f"known weight rows: {known_weight_rows}")
    print(f"manual review rows: {review_rows}")
    print(f"output: {args.output}")


if __name__ == "__main__":
    main()
