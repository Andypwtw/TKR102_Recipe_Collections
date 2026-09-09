from __future__ import annotations

from pathlib import Path
import sys

PYTHON_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = PYTHON_DIR.parent
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))

from app.db import get_connection


NUTRIENT_COLUMNS = [
    "energy_kcal", "protein_g", "fat_g", "carbohydrate_g", "dietary_fiber_g",
    "sodium_mg", "potassium_mg", "calcium_mg", "magnesium_mg", "iron_mg",
    "zinc_mg", "phosphorus_mg", "vitamin_a_re_ug", "vitamin_b1_mg",
    "vitamin_b2_mg", "niacin_mg", "vitamin_b6_mg", "vitamin_b12_ug",
    "folate_ug", "vitamin_c_mg", "vitamin_e_mg", "cholesterol_mg",
]


def main() -> None:
    with get_connection() as conn, conn.cursor() as cursor:
        cursor.execute("SELECT id FROM recipes ORDER BY id")
        recipe_ids = [row["id"] for row in cursor.fetchall()]

        for index, recipe_id in enumerate(recipe_ids, start=1):
            cursor.execute(
                """
                SELECT
                    ri.weight_g,
                    ns.*
                FROM recipe_ingredients ri
                LEFT JOIN ingredient_nutrition_map inm ON inm.ingredient_id = ri.ingredient_id
                LEFT JOIN nutrition_source ns ON ns.id = inm.nutrition_source_id
                WHERE ri.recipe_id=%s
                """,
                (recipe_id,),
            )
            rows = cursor.fetchall()
            totals = {column: 0.0 for column in NUTRIENT_COLUMNS}
            known_weight_g = 0.0
            matched_rows = 0

            for row in rows:
                weight_g = row.get("weight_g")
                nutrition_id = row.get("id")
                if weight_g is None or nutrition_id is None:
                    continue
                weight_g = float(weight_g)
                known_weight_g += weight_g
                matched_rows += 1
                factor = weight_g / 100.0
                for column in NUTRIENT_COLUMNS:
                    value = row.get(column)
                    if value is not None:
                        totals[column] += float(value) * factor

            total_rows = len(rows)
            coverage = (matched_rows / total_rows * 100.0) if total_rows else 0.0
            cols = [
                "recipe_id", "known_weight_g", "total_ingredient_rows", "matched_ingredient_rows",
                "coverage_percent", *NUTRIENT_COLUMNS,
            ]
            values = [recipe_id, known_weight_g, total_rows, matched_rows, coverage, *[totals[c] for c in NUTRIENT_COLUMNS]]
            placeholders = ",".join(["%s"] * len(cols))
            update_clause = ",".join(f"{c}=VALUES({c})" for c in cols if c != "recipe_id")
            cursor.execute(
                f"INSERT INTO recipe_nutrition_summary ({','.join(cols)}) VALUES ({placeholders}) "
                f"ON DUPLICATE KEY UPDATE {update_clause}",
                values,
            )

            if index % 500 == 0:
                conn.commit()
                print(f"calculated {index}/{len(recipe_ids)} recipes")

    print(f"done: {len(recipe_ids)} recipes")


if __name__ == "__main__":
    main()
