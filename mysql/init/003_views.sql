USE recipe_ai;

CREATE OR REPLACE VIEW v_recipe_detail AS
SELECT
    r.id AS recipe_id,
    r.seq,
    r.name AS recipe_name,
    r.published_date,
    r.source_url,
    ri.line_no,
    i.canonical_name AS ingredient_name,
    ri.raw_amount_text,
    ri.quantity_value,
    u.canonical_unit,
    ri.weight_g,
    ri.needs_manual_review
FROM recipes r
JOIN recipe_ingredients ri ON ri.recipe_id = r.id
JOIN ingredients i ON i.id = ri.ingredient_id
LEFT JOIN units u ON u.id = ri.unit_id;

CREATE OR REPLACE VIEW v_recipe_calorie AS
SELECT
    r.seq,
    r.name,
    s.energy_kcal,
    s.coverage_percent,
    s.known_weight_g
FROM recipes r
LEFT JOIN recipe_nutrition_summary s ON s.recipe_id = r.id;
