from __future__ import annotations

from app.db import get_connection


ENERGY_SOURCE_COLUMN = "熱量(kcal)"


def main():
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "DELETE FROM recipe_nutrition_summary"
        )

        cur.execute(
            """
            INSERT INTO recipe_nutrition_summary
            (
                recipe_id,
                energy_kcal,
                coverage_percent,
                calculated_at
            )

            SELECT
                ri.recipe_id,

                ROUND(
                    SUM(
                        CASE
                            WHEN ri.weight_g IS NOT NULL
                             AND energy.energy_kcal_per_100g
                                 IS NOT NULL
                            THEN
                                energy.energy_kcal_per_100g
                                * ri.weight_g / 100
                            ELSE 0
                        END
                    ),
                    2
                ) AS energy_kcal,

                ROUND(
                    100 * SUM(
                        CASE
                            WHEN ri.weight_g IS NOT NULL
                             AND energy.energy_kcal_per_100g
                                 IS NOT NULL
                            THEN 1
                            ELSE 0
                        END
                    ) / COUNT(*),
                    2
                ) AS coverage_percent,

                NOW()

            FROM recipe_ingredients ri

            LEFT JOIN ingredient_nutrition_map inm
              ON inm.ingredient_id = ri.ingredient_id
             AND inm.status = 'APPROVED'

            LEFT JOIN (
                SELECT
                    nv.nutrition_source_id,
                    nv.value_numeric
                      AS energy_kcal_per_100g

                FROM nutrition_values nv

                JOIN nutrient_definitions nd
                  ON nd.id = nv.nutrient_id

                WHERE nd.source_column_name = %s
            ) energy
              ON energy.nutrition_source_id
               = inm.nutrition_source_id

            GROUP BY ri.recipe_id
            """,
            (ENERGY_SOURCE_COLUMN,),
        )

        cur.execute(
            """
            SELECT
                COUNT(*) AS recipe_count,
                ROUND(AVG(energy_kcal), 2)
                    AS avg_kcal,
                ROUND(MIN(energy_kcal), 2)
                    AS min_kcal,
                ROUND(MAX(energy_kcal), 2)
                    AS max_kcal,
                ROUND(AVG(coverage_percent), 2)
                    AS avg_coverage
            FROM recipe_nutrition_summary
            """
        )

        summary = cur.fetchone()

        conn.commit()

    print("Recipe calorie summary calculated.")
    print(
        f"Energy source column: "
        f"{ENERGY_SOURCE_COLUMN}"
    )
    print(summary)


if __name__ == "__main__":
    main()
