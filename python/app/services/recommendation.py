from __future__ import annotations
from app.db import get_connection

def recommend_by_ingredients(ingredients: list[str], limit: int = 10):
    if not ingredients:
        return []
    patterns = [f"%{x.strip()}%" for x in ingredients if x.strip()]
    if not patterns:
        return []
    where = " OR ".join(["i.canonical_name LIKE %s"] * len(patterns))
    sql = f"""
        SELECT r.seq, r.name,
               COUNT(DISTINCT i.id) AS matched_ingredients
        FROM recipes r
        JOIN recipe_ingredients ri ON ri.recipe_id = r.id
        JOIN ingredients i ON i.id = ri.ingredient_id
        WHERE {where}
        GROUP BY r.id, r.seq, r.name
        ORDER BY matched_ingredients DESC, r.seq
        LIMIT %s
    """
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(sql, (*patterns, limit))
        return cur.fetchall()
