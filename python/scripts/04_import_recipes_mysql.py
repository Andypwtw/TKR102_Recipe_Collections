from __future__ import annotations
import json
from pathlib import Path
from app.db import get_connection

SRC=Path("/workspace/data/processed/recipes_normalized.json")

def main():
    rows=json.loads(SRC.read_text(encoding="utf-8"))
    with get_connection() as conn, conn.cursor() as cur:
        for r in rows:
            cur.execute(
                """
                INSERT INTO recipes(seq,name,published_date,source_url,raw_keywords,steps)
                VALUES(%s,%s,NULL,%s,%s,%s)
                ON DUPLICATE KEY UPDATE
                  name=VALUES(name), source_url=VALUES(source_url),
                  raw_keywords=VALUES(raw_keywords), steps=VALUES(steps)
                """,
                (r["seq"], r["name"], r["source_url"], r["raw_keywords"], r["steps"])
            )
            cur.execute("SELECT id FROM recipes WHERE seq=%s",(r["seq"],))
            recipe_id=cur.fetchone()["id"]
            cur.execute("DELETE FROM recipe_ingredients WHERE recipe_id=%s",(recipe_id,))
            for ing in r["ingredients"]:
                name=ing["canonical_name"]
                cur.execute(
                    "INSERT INTO ingredients(canonical_name) VALUES(%s) ON DUPLICATE KEY UPDATE canonical_name=VALUES(canonical_name)",
                    (name,)
                )
                cur.execute("SELECT id FROM ingredients WHERE canonical_name=%s",(name,))
                ingredient_id=cur.fetchone()["id"]
                unit_id=None
                if ing["unit"]:
                    cur.execute(
                        "INSERT INTO units(canonical_unit,unit_type) VALUES(%s,'unknown') ON DUPLICATE KEY UPDATE canonical_unit=VALUES(canonical_unit)",
                        (ing["unit"],)
                    )
                    cur.execute("SELECT id FROM units WHERE canonical_unit=%s",(ing["unit"],))
                    unit_id=cur.fetchone()["id"]
                cur.execute(
                    """
                    INSERT INTO recipe_ingredients
                    (recipe_id,line_no,raw_text,raw_name,ingredient_id,quantity_value,unit_id,weight_g)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (recipe_id,ing["line_no"],ing["raw_text"],ing["raw_name"],ingredient_id,ing["quantity_value"],unit_id,ing["weight_g"])
                )
        conn.commit()
    print(f"imported recipes={len(rows)}")

if __name__ == "__main__":
    main()
