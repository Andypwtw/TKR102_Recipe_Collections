from __future__ import annotations

from app.db import get_connection


def recommend_by_ingredients(
    ingredients: list[str],
    limit: int = 10,
):
    if not ingredients:
        return []

    patterns = [
        f"%{name.strip()}%"
        for name in ingredients
        if name.strip()
    ]

    if not patterns:
        return []

    where = " OR ".join(
        ["i.canonical_name LIKE %s"] * len(patterns)
    )

    sql = f"""
        SELECT
            r.seq,
            r.name,
            COUNT(DISTINCT i.id) AS matched_ingredients,
            ROUND(rns.energy_kcal, 2) AS energy_kcal,
            ROUND(
                rns.coverage_percent,
                2
            ) AS calorie_coverage_percent

        FROM recipes r

        JOIN recipe_ingredients ri
          ON ri.recipe_id = r.id

        JOIN ingredients i
          ON i.id = ri.ingredient_id

        LEFT JOIN recipe_nutrition_summary rns
          ON rns.recipe_id = r.id

        WHERE {where}

        GROUP BY
            r.id,
            r.seq,
            r.name,
            rns.energy_kcal,
            rns.coverage_percent

        ORDER BY
            matched_ingredients DESC,
            r.seq

        LIMIT %s
    """

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            sql,
            (*patterns, limit),
        )

        return cur.fetchall()
