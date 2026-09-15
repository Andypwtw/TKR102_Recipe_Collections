CREATE DATABASE IF NOT EXISTS recipe_ai CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE recipe_ai;

CREATE TABLE IF NOT EXISTS recipes (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  seq VARCHAR(50) NOT NULL UNIQUE,
  name VARCHAR(255) NOT NULL,
  published_date DATE NULL,
  source_url VARCHAR(500),
  raw_keywords TEXT,
  steps LONGTEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ingredients (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  canonical_name VARCHAR(255) NOT NULL UNIQUE,
  category VARCHAR(100),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS units (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  canonical_unit VARCHAR(50) NOT NULL UNIQUE,
  unit_type VARCHAR(50) NOT NULL DEFAULT 'unknown',
  to_gram_factor DECIMAL(18,6),
  to_ml_factor DECIMAL(18,6),
  is_qualitative BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS recipe_ingredients (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  recipe_id BIGINT NOT NULL,
  line_no INT NOT NULL,
  raw_text VARCHAR(1000),
  raw_name VARCHAR(255),
  ingredient_id BIGINT,
  raw_amount_text VARCHAR(255),
  quantity_min DECIMAL(18,6),
  quantity_max DECIMAL(18,6),
  quantity_value DECIMAL(18,6),
  unit_id BIGINT,
  weight_g DECIMAL(18,6),
  is_estimated BOOLEAN DEFAULT FALSE,
  needs_manual_review BOOLEAN DEFAULT FALSE,
  review_reason VARCHAR(500),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_recipe_line(recipe_id,line_no),
  CONSTRAINT fk_ri_recipe FOREIGN KEY(recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
  CONSTRAINT fk_ri_ing FOREIGN KEY(ingredient_id) REFERENCES ingredients(id),
  CONSTRAINT fk_ri_unit FOREIGN KEY(unit_id) REFERENCES units(id)
);

CREATE TABLE IF NOT EXISTS ingredient_unit_weights (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  ingredient_id BIGINT NOT NULL,
  unit_id BIGINT NOT NULL,
  grams_per_unit DECIMAL(18,6) NOT NULL,
  confidence VARCHAR(20),
  status VARCHAR(20) DEFAULT 'ACTIVE',
  source VARCHAR(255),
  note VARCHAR(500),
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_iuw(ingredient_id,unit_id),
  CONSTRAINT fk_iuw_ing FOREIGN KEY(ingredient_id) REFERENCES ingredients(id),
  CONSTRAINT fk_iuw_unit FOREIGN KEY(unit_id) REFERENCES units(id)
);

CREATE TABLE IF NOT EXISTS ingredient_densities (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  ingredient_id BIGINT NOT NULL UNIQUE,
  density_g_ml DECIMAL(18,6) NOT NULL,
  density_type VARCHAR(32) DEFAULT 'liquid',
  confidence VARCHAR(20),
  status VARCHAR(20) DEFAULT 'ACTIVE',
  source VARCHAR(255),
  note VARCHAR(500),
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_density_ing FOREIGN KEY(ingredient_id) REFERENCES ingredients(id)
);

CREATE TABLE IF NOT EXISTS nutrition_source (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  food_code VARCHAR(100),
  food_name VARCHAR(255) NOT NULL,
  food_category VARCHAR(255),
  energy_kcal DECIMAL(18,6),
  protein_g DECIMAL(18,6),
  fat_g DECIMAL(18,6),
  carbohydrate_g DECIMAL(18,6),
  sodium_mg DECIMAL(18,6),
  raw_data JSON,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ingredient_nutrition_map (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  ingredient_id BIGINT NOT NULL UNIQUE,
  nutrition_source_id BIGINT NOT NULL,
  match_method VARCHAR(50),
  match_score DECIMAL(8,6),
  status VARCHAR(20),
  reviewed_at TIMESTAMP NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_inm_ing FOREIGN KEY(ingredient_id) REFERENCES ingredients(id),
  CONSTRAINT fk_inm_ns FOREIGN KEY(nutrition_source_id) REFERENCES nutrition_source(id)
);

CREATE TABLE IF NOT EXISTS manual_review (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  ingredient_id BIGINT NOT NULL,
  candidate_nutrition_id BIGINT,
  candidate_name VARCHAR(255),
  score DECIMAL(8,6),
  status VARCHAR(20) DEFAULT 'PENDING',
  note VARCHAR(500),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  reviewed_at TIMESTAMP NULL,
  CONSTRAINT fk_mr_ing FOREIGN KEY(ingredient_id) REFERENCES ingredients(id),
  CONSTRAINT fk_mr_ns FOREIGN KEY(candidate_nutrition_id) REFERENCES nutrition_source(id)
);

CREATE TABLE IF NOT EXISTS recipe_nutrition_summary (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  recipe_id BIGINT NOT NULL UNIQUE,
  energy_kcal DECIMAL(18,6),
  protein_g DECIMAL(18,6),
  fat_g DECIMAL(18,6),
  carbohydrate_g DECIMAL(18,6),
  sodium_mg DECIMAL(18,6),
  coverage_percent DECIMAL(8,2),
  calculated_at TIMESTAMP NULL,
  CONSTRAINT fk_rns_recipe FOREIGN KEY(recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
);
