from __future__ import annotations

from collections import defaultdict

from app.db import get_connection
from app.services.normalization import load_alias_map, standardize_ingredient_name
from app.paths import REFERENCE_DIR

ALIASES_PATH = REFERENCE_DIR / "ingredient_aliases.json"


def _normalize_inputs(items: list[str]) -> list[str]:
    aliases = load_alias_map(ALIASES_PATH)
    result = []
    for item in items:
        name = standardize_ingredient_name(item, aliases)
        if name and name not in result:
            result.append(name)
    return result


def recommend_by_ingredients(ingredients: list[str], limit: int = 5) -> list[dict]:
    requested = set(_normalize_inputs(ingredients))
    if not requested:
        return []

    with get_connection() as conn, conn.cursor() as cursor:
        placeholders = ",".join(["%s"] * len(requested))
        cursor.execute(
            f"""
            SELECT DISTINCT r.id, r.seq, r.name, r.source_url
            FROM recipes r
            JOIN recipe_ingredients ri ON ri.recipe_id = r.id
            JOIN ingredients i ON i.id = ri.ingredient_id
            WHERE i.canonical_name IN ({placeholders})
            """,
            tuple(requested),
        )
        recipes = cursor.fetchall()
        if not recipes:
            return []

        recipe_ids = [row["id"] for row in recipes]
        recipe_placeholders = ",".join(["%s"] * len(recipe_ids))
        cursor.execute(
            f"""
            SELECT ri.recipe_id, i.canonical_name
            FROM recipe_ingredients ri
            JOIN ingredients i ON i.id = ri.ingredient_id
            WHERE ri.recipe_id IN ({recipe_placeholders})
            """,
            tuple(recipe_ids),
        )
        ingredient_rows = cursor.fetchall()

        cursor.execute(
            f"""
            SELECT rns.recipe_id, rns.energy_kcal, rns.coverage_percent
            FROM recipe_nutrition_summary rns
            WHERE rns.recipe_id IN ({recipe_placeholders})
            """,
            tuple(recipe_ids),
        )
        nutrition = {row["recipe_id"]: row for row in cursor.fetchall()}

    recipe_ingredients: dict[int, set[str]] = defaultdict(set)
    for row in ingredient_rows:
        recipe_ingredients[row["recipe_id"]].add(row["canonical_name"])

    scored = []
    for recipe in recipes:
        actual = recipe_ingredients[recipe["id"]]
        intersection = requested & actual
        union = requested | actual
        jaccard = len(intersection) / len(union) if union else 0.0
        coverage = len(intersection) / len(requested) if requested else 0.0
        nut = nutrition.get(recipe["id"], {})
        scored.append(
            {
                "seq": recipe["seq"],
                "name": recipe["name"],
                "source_url": recipe["source_url"],
                "matched_ingredients": sorted(intersection),
                "requested_coverage": round(coverage, 4),
                "jaccard_score": round(jaccard, 4),
                "energy_kcal": float(nut["energy_kcal"]) if nut.get("energy_kcal") is not None else None,
                "nutrition_coverage_percent": float(nut["coverage_percent"]) if nut.get("coverage_percent") is not None else None,
            }
        )

    scored.sort(key=lambda x: (x["requested_coverage"], x["jaccard_score"]), reverse=True)
    return scored[: max(1, min(limit, 50))]
