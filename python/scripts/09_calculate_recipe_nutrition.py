from __future__ import annotations
from app.db import get_connection

def main():
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM recipe_nutrition_summary")
        cur.execute(
            """
            INSERT INTO recipe_nutrition_summary
            (recipe_id,energy_kcal,protein_g,fat_g,carbohydrate_g,sodium_mg,coverage_percent,calculated_at)
            SELECT
              ri.recipe_id,
              SUM(COALESCE(ns.energy_kcal,0) * ri.weight_g / 100),
              SUM(COALESCE(ns.protein_g,0) * ri.weight_g / 100),
              SUM(COALESCE(ns.fat_g,0) * ri.weight_g / 100),
              SUM(COALESCE(ns.carbohydrate_g,0) * ri.weight_g / 100),
              SUM(COALESCE(ns.sodium_mg,0) * ri.weight_g / 100),
              100 * SUM(CASE WHEN ri.weight_g IS NOT NULL AND inm.nutrition_source_id IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*),
              NOW()
            FROM recipe_ingredients ri
            LEFT JOIN ingredient_nutrition_map inm
              ON inm.ingredient_id=ri.ingredient_id AND inm.status='APPROVED'
            LEFT JOIN nutrition_source ns ON ns.id=inm.nutrition_source_id
            GROUP BY ri.recipe_id
            """
        )
        conn.commit()
    print("recipe nutrition summary calculated")

if __name__ == "__main__":
    main()
