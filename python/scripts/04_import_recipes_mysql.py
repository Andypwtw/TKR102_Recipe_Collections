from __future__ import annotations

import argparse
import json
from pathlib import Path

import sys

PYTHON_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = PYTHON_DIR.parent
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))

from app.db import get_connection


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import normalized recipes into MySQL.")
    parser.add_argument("--input", type=Path, default=PROJECT_ROOT / "data" / "processed" / "recipes_normalized.json")
    return parser.parse_args()


def get_or_create_id(cursor, table: str, unique_column: str, value: str) -> int:
    cursor.execute(
        f"INSERT INTO {table} ({unique_column}) VALUES (%s) ON DUPLICATE KEY UPDATE id = LAST_INSERT_ID(id)",
        (value,),
    )
    return int(cursor.lastrowid)


def main() -> None:
    args = parse_args()
    count = 0

    recipes = json.loads(args.input.read_text(encoding="utf-8"))
    with get_connection() as conn, conn.cursor() as cursor:
        for recipe in recipes:
            cursor.execute(
                """
                INSERT INTO recipes (seq, name, published_date, source_url, raw_keywords, steps)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    id = LAST_INSERT_ID(id),
                    name = VALUES(name),
                    published_date = VALUES(published_date),
                    source_url = VALUES(source_url),
                    raw_keywords = VALUES(raw_keywords),
                    steps = VALUES(steps)
                """,
                (
                    recipe["seq"], recipe["name"], recipe.get("published_date"),
                    recipe.get("source_url"), recipe.get("raw_keywords"), recipe.get("steps"),
                ),
            )
            recipe_id = int(cursor.lastrowid)

            cursor.execute("DELETE FROM recipe_keywords WHERE recipe_id=%s", (recipe_id,))
            for keyword in recipe.get("keywords", []):
                keyword_id = get_or_create_id(cursor, "keywords", "name", keyword)
                cursor.execute(
                    "INSERT IGNORE INTO recipe_keywords (recipe_id, keyword_id) VALUES (%s, %s)",
                    (recipe_id, keyword_id),
                )

            cursor.execute("DELETE FROM recipe_ingredients WHERE recipe_id=%s", (recipe_id,))
            for item in recipe.get("materials", []):
                ingredient_id = get_or_create_id(cursor, "ingredients", "canonical_name", item["canonical_name"])
                raw_name = item.get("raw_name") or item["canonical_name"]
                cursor.execute(
                    """
                    INSERT INTO ingredient_aliases (ingredient_id, alias_name, source)
                    VALUES (%s, %s, 'ytower')
                    ON DUPLICATE KEY UPDATE ingredient_id=VALUES(ingredient_id)
                    """,
                    (ingredient_id, raw_name),
                )

                unit_id = None
                if item.get("canonical_unit"):
                    cursor.execute("SELECT id FROM units WHERE canonical_unit=%s", (item["canonical_unit"],))
                    row = cursor.fetchone()
                    if row:
                        unit_id = row["id"]
                    else:
                        cursor.execute(
                            "INSERT INTO units (canonical_unit, unit_type) VALUES (%s, 'unknown')",
                            (item["canonical_unit"],),
                        )
                        unit_id = cursor.lastrowid

                cursor.execute(
                    """
                    INSERT INTO recipe_ingredients (
                        recipe_id, line_no, raw_text, raw_name, ingredient_id, raw_amount_text,
                        quantity_min, quantity_max, quantity_value, unit_id, weight_g,
                        is_estimated, needs_manual_review, review_reason
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        recipe_id, item["line_no"], item["raw_text"], raw_name, ingredient_id,
                        item.get("raw_amount_text"), item.get("quantity_min"), item.get("quantity_max"),
                        item.get("quantity_value"), unit_id, item.get("weight_g"),
                        int(bool(item.get("is_estimated"))), int(bool(item.get("needs_manual_review"))),
                        item.get("review_reason"),
                    ),
                )

            count += 1
            if count % 500 == 0:
                conn.commit()
                print(f"imported {count} recipes")

    print(f"done: {count} recipes")


if __name__ == "__main__":
    main()
