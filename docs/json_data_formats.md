# JSON 資料檔格式

本版所有 Python ETL 產生的資料檔統一使用 UTF-8 JSON。

- `recipes_clean.json`: JSON array，每個元素是一道清洗後食譜。
- `recipes_normalized.json`: JSON array，每個元素是一道正規化食譜。
- `unit_weight_map.json`: JSON array，食材+單位的克重對照。
- `unit_weight_candidates.json`: JSON array，含 ACTIVE/REVIEW 候選。
- `unit_weight_pending_top500.json`: JSON array，待補高頻組合。
- `ingredient_aliases.json`: JSON array，同義詞對照。
- `ingredient_density_map.json`: JSON array，食材密度 g/ml 對照。
- `manual_review.json`: JSON array，人工審核輸入/輸出。

所有輸出均使用 `ensure_ascii=False`，中文直接以 UTF-8 儲存。
