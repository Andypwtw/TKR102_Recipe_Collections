# Recipe Collections - 完整營養資料保留 / 目前只顯示熱量

## 這一版的營養策略

2025 食品營養 Excel **全部匯入 MySQL**。

不是只保存熱量。

完整 Excel 會正規化成：

```text
nutrition_source
+
nutrient_definitions
+
nutrition_values
```

同時 `nutrition_source.raw_data`
保留每一列 Excel 的完整原始 JSON，
確保來源資料可以完整追溯。

目前應用功能只使用：

```text
熱量(kcal)
```

因此：

```text
09_calculate_recipe_nutrition.py
```

只讀：

```text
nutrient_definitions.source_column_name
=
熱量(kcal)
```

未來增加蛋白質、脂肪、鈉、維生素等功能時，
不需要重新匯入或重新設計營養資料庫。

---

## 營養匯入

Excel 必須位於：

```text
data/reference/food_nutrition_2025.xlsx
```

本下載包已包含目前的 2025 食品營養資料 Excel。

執行：

```bash
docker compose exec python bash
cd /workspace/python
uv run python scripts/05_import_nutrition_excel.py
```

---

## 已有舊 MySQL 資料庫時

先執行：

```bash
uv run python scripts/00_migrate_full_nutrition.py
```

然後重新跑：

```bash
uv run python scripts/10_pipeline.py
```

---

## ER Model

本專案 `docs/` 已加入：

```text
ER_Model_正規化.png
ER_Model_正規化.xlsx
er_model.dbml
ER_MODEL_中文詳細說明.md
```

`er_model.dbml` 可以直接貼到：

```text
dbdiagram.io
```

產生互動式 ER Model。

---

## 完整自動資料流

```text
Airflow
→ YTower Crawler
→ Kafka
→ MongoDB raw_recipes
→ Python ETL
→ MySQL Recipe Tables
→ 完整 Nutrition Excel Import
→ Nutrition Matching
→ Auto Review
→ Ingredient Nutrition Map
→ 目前只計算 energy_kcal
→ Flask API
→ Hermes / LINE
```

## 注意

這一版仍保留之前的重要限制：

`crawler/ytower_crawler.py` 需要放入你真正已驗證的 YTower 爬蟲邏輯。
