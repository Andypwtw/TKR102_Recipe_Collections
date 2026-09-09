CREATE DATABASE IF NOT EXISTS recipe_ai
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;

USE recipe_ai;

CREATE TABLE IF NOT EXISTS recipes (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    seq VARCHAR(32) NOT NULL,
    name VARCHAR(255) NOT NULL,
    published_date DATE NULL,
    source_url VARCHAR(1024) NULL,
    raw_keywords TEXT NULL,
    steps LONGTEXT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_recipes_seq (seq),
    KEY idx_recipes_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS keywords (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    UNIQUE KEY uk_keywords_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS recipe_keywords (
    recipe_id BIGINT UNSIGNED NOT NULL,
    keyword_id BIGINT UNSIGNED NOT NULL,
    PRIMARY KEY (recipe_id, keyword_id),
    CONSTRAINT fk_recipe_keywords_recipe
        FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
    CONSTRAINT fk_recipe_keywords_keyword
        FOREIGN KEY (keyword_id) REFERENCES keywords(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS ingredients (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    canonical_name VARCHAR(255) NOT NULL,
    category VARCHAR(120) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_ingredients_name (canonical_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS ingredient_aliases (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    ingredient_id BIGINT UNSIGNED NOT NULL,
    alias_name VARCHAR(255) NOT NULL,
    source VARCHAR(50) NOT NULL DEFAULT 'dictionary',
    UNIQUE KEY uk_alias_name (alias_name),
    KEY idx_alias_ingredient (ingredient_id),
    CONSTRAINT fk_alias_ingredient
        FOREIGN KEY (ingredient_id) REFERENCES ingredients(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS units (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    canonical_unit VARCHAR(64) NOT NULL,
    unit_type VARCHAR(32) NOT NULL,
    to_gram_factor DECIMAL(18,6) NULL,
    to_ml_factor DECIMAL(18,6) NULL,
    is_qualitative TINYINT(1) NOT NULL DEFAULT 0,
    UNIQUE KEY uk_units_name (canonical_unit)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS ingredient_unit_weights (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    ingredient_id BIGINT UNSIGNED NOT NULL,
    unit_id BIGINT UNSIGNED NOT NULL,
    grams_per_unit DECIMAL(18,6) NOT NULL,
    source VARCHAR(255) NULL,
    note VARCHAR(500) NULL,
    UNIQUE KEY uk_ingredient_unit (ingredient_id, unit_id),
    CONSTRAINT fk_iuw_ingredient
        FOREIGN KEY (ingredient_id) REFERENCES ingredients(id) ON DELETE CASCADE,
    CONSTRAINT fk_iuw_unit
        FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS ingredient_densities (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    ingredient_id BIGINT UNSIGNED NOT NULL,
    density_g_ml DECIMAL(18,6) NOT NULL,
    density_type VARCHAR(32) NOT NULL DEFAULT 'liquid',
    confidence VARCHAR(20) NOT NULL DEFAULT '中',
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    source VARCHAR(255) NULL,
    note VARCHAR(500) NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_ingredient_density (ingredient_id),
    CONSTRAINT fk_density_ingredient
        FOREIGN KEY (ingredient_id) REFERENCES ingredients(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS recipe_ingredients (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    recipe_id BIGINT UNSIGNED NOT NULL,
    line_no INT NOT NULL,
    raw_text VARCHAR(1000) NOT NULL,
    raw_name VARCHAR(255) NULL,
    ingredient_id BIGINT UNSIGNED NOT NULL,
    raw_amount_text VARCHAR(255) NULL,
    quantity_min DECIMAL(18,6) NULL,
    quantity_max DECIMAL(18,6) NULL,
    quantity_value DECIMAL(18,6) NULL,
    unit_id BIGINT UNSIGNED NULL,
    weight_g DECIMAL(18,6) NULL,
    is_estimated TINYINT(1) NOT NULL DEFAULT 0,
    needs_manual_review TINYINT(1) NOT NULL DEFAULT 0,
    review_reason VARCHAR(500) NULL,
    UNIQUE KEY uk_recipe_line (recipe_id, line_no),
    KEY idx_ri_ingredient (ingredient_id),
    CONSTRAINT fk_ri_recipe
        FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
    CONSTRAINT fk_ri_ingredient
        FOREIGN KEY (ingredient_id) REFERENCES ingredients(id),
    CONSTRAINT fk_ri_unit
        FOREIGN KEY (unit_id) REFERENCES units(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS nutrition_source (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    source_code VARCHAR(50) NOT NULL,
    food_category VARCHAR(120) NULL,
    sample_name VARCHAR(255) NOT NULL,
    content_description TEXT NULL,
    common_name TEXT NULL,
    waste_rate_pct DECIMAL(18,6) NULL,
    energy_kcal DECIMAL(18,6) NULL,
    corrected_energy_kcal DECIMAL(18,6) NULL,
    water_g DECIMAL(18,6) NULL,
    protein_g DECIMAL(18,6) NULL,
    fat_g DECIMAL(18,6) NULL,
    saturated_fat_g DECIMAL(18,6) NULL,
    carbohydrate_g DECIMAL(18,6) NULL,
    dietary_fiber_g DECIMAL(18,6) NULL,
    sodium_mg DECIMAL(18,6) NULL,
    potassium_mg DECIMAL(18,6) NULL,
    calcium_mg DECIMAL(18,6) NULL,
    magnesium_mg DECIMAL(18,6) NULL,
    iron_mg DECIMAL(18,6) NULL,
    zinc_mg DECIMAL(18,6) NULL,
    phosphorus_mg DECIMAL(18,6) NULL,
    vitamin_a_re_ug DECIMAL(18,6) NULL,
    vitamin_b1_mg DECIMAL(18,6) NULL,
    vitamin_b2_mg DECIMAL(18,6) NULL,
    niacin_mg DECIMAL(18,6) NULL,
    vitamin_b6_mg DECIMAL(18,6) NULL,
    vitamin_b12_ug DECIMAL(18,6) NULL,
    folate_ug DECIMAL(18,6) NULL,
    vitamin_c_mg DECIMAL(18,6) NULL,
    vitamin_e_mg DECIMAL(18,6) NULL,
    cholesterol_mg DECIMAL(18,6) NULL,
    raw_data JSON NOT NULL,
    source_version VARCHAR(50) NOT NULL DEFAULT '2025',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_nutrition_source_code (source_code),
    KEY idx_nutrition_sample_name (sample_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS ingredient_nutrition_map (
    ingredient_id BIGINT UNSIGNED PRIMARY KEY,
    nutrition_source_id BIGINT UNSIGNED NOT NULL,
    match_method VARCHAR(50) NOT NULL,
    match_score DECIMAL(8,6) NOT NULL DEFAULT 1,
    status VARCHAR(20) NOT NULL DEFAULT 'AUTO',
    reviewed_at DATETIME NULL,
    CONSTRAINT fk_inm_ingredient
        FOREIGN KEY (ingredient_id) REFERENCES ingredients(id) ON DELETE CASCADE,
    CONSTRAINT fk_inm_nutrition
        FOREIGN KEY (nutrition_source_id) REFERENCES nutrition_source(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS manual_review (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    ingredient_id BIGINT UNSIGNED NOT NULL,
    candidate_nutrition_id BIGINT UNSIGNED NULL,
    candidate_name VARCHAR(255) NULL,
    score DECIMAL(8,6) NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    note VARCHAR(500) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reviewed_at DATETIME NULL,
    KEY idx_manual_status (status),
    CONSTRAINT fk_manual_ingredient
        FOREIGN KEY (ingredient_id) REFERENCES ingredients(id) ON DELETE CASCADE,
    CONSTRAINT fk_manual_nutrition
        FOREIGN KEY (candidate_nutrition_id) REFERENCES nutrition_source(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS recipe_nutrition_summary (
    recipe_id BIGINT UNSIGNED PRIMARY KEY,
    known_weight_g DECIMAL(18,6) NOT NULL DEFAULT 0,
    total_ingredient_rows INT NOT NULL DEFAULT 0,
    matched_ingredient_rows INT NOT NULL DEFAULT 0,
    coverage_percent DECIMAL(8,3) NOT NULL DEFAULT 0,
    energy_kcal DECIMAL(18,6) NULL,
    protein_g DECIMAL(18,6) NULL,
    fat_g DECIMAL(18,6) NULL,
    carbohydrate_g DECIMAL(18,6) NULL,
    dietary_fiber_g DECIMAL(18,6) NULL,
    sodium_mg DECIMAL(18,6) NULL,
    potassium_mg DECIMAL(18,6) NULL,
    calcium_mg DECIMAL(18,6) NULL,
    magnesium_mg DECIMAL(18,6) NULL,
    iron_mg DECIMAL(18,6) NULL,
    zinc_mg DECIMAL(18,6) NULL,
    phosphorus_mg DECIMAL(18,6) NULL,
    vitamin_a_re_ug DECIMAL(18,6) NULL,
    vitamin_b1_mg DECIMAL(18,6) NULL,
    vitamin_b2_mg DECIMAL(18,6) NULL,
    niacin_mg DECIMAL(18,6) NULL,
    vitamin_b6_mg DECIMAL(18,6) NULL,
    vitamin_b12_ug DECIMAL(18,6) NULL,
    folate_ug DECIMAL(18,6) NULL,
    vitamin_c_mg DECIMAL(18,6) NULL,
    vitamin_e_mg DECIMAL(18,6) NULL,
    cholesterol_mg DECIMAL(18,6) NULL,
    calculated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_rns_recipe
        FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS etl_runs (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    pipeline_name VARCHAR(100) NOT NULL,
    started_at DATETIME NOT NULL,
    finished_at DATETIME NULL,
    status VARCHAR(20) NOT NULL,
    processed_rows INT NOT NULL DEFAULT 0,
    message TEXT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
