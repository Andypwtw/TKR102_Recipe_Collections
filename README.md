# Recipe Collections v2 — 食譜資料清洗、正規化、MySQL、Flask API、Hermes 串接完整教學

## v2.4 FIXED：統一 Docker + VS Code + uv 開發環境

這一版修正了先前 `.venv`、`/opt/venv`、`PYTHONPATH` 與 `/workspace` 混用的問題。正式開發固定使用：

```text
Python container: recipe-python
Workspace:        /workspace
Python project:   /workspace/python
uv environment:  /opt/venv
Python:           /opt/venv/bin/python
PYTHONPATH:       /workspace/python
MySQL host:       mysql:3306 (container 內)
Workbench:        127.0.0.1:3307 (Mac)
```

### 第一次啟動

```bash
cp .env.example .env
docker compose up -d --build
docker compose ps
```

### VS Code 進入 container

建議使用 `Dev Containers: Reopen in Container`，此專案已提供 `.devcontainer/devcontainer.json`。進入後先執行：

```bash
cd /workspace/python
uv run python scripts/00_check_environment.py
```

確認後再執行：

```bash
uv run python scripts/10_pipeline.py
```

**不要再使用 `/workspace/python/.venv/bin/python`。** 這個專案的 uv 環境固定在 `/opt/venv`。

---

> **v2.3 JSON 格式統一**：本版將 ETL/正規化程式產生的中間檔、reference mapping 與人工審核檔全部統一為標準 `.json` 陣列格式。原始營養 Excel 屬外部來源資料，因此仍保留 `.xlsx`；MySQL SQL/DBML/Docker 設定檔也不屬資料輸出格式，因此維持原格式。


本版本依照目前最後確定的流程重新整理，重點是：

1. **先分別建立 MySQL container 與 Python container，確認各自能運作。**
2. **再使用 Docker Compose 一次建立兩個 container。**
3. MySQL 使用 **MySQL Workbench**，開發階段先以 `root` 登入。
4. Python 使用 **VS Code** 連進 container 開發。
5. Python 套件使用 **uv** 管理，不使用傳統 `pip install -r requirements.txt` 作為主要流程。
6. 清洗與正規化直接使用 `data/raw/ytower_seq_recipes.json`。
7. 食品營養成分資料庫完整列資料保存在 MySQL `nutrition_source.raw_data` JSON，同時抽取系統會使用的營養欄位。
8. Flask 提供 REST API，另外提供 `/api/v1/hermes/recommend` 與 `/openapi.json`，讓 Hermes 可以用 HTTP / OpenAPI 方式調用。
9. 最後提供 `docs/er_model.dbml`，可以直接貼到 dbdiagram.io。

---

## 1. 這一版的資料來源

### 食譜 JSON

檔案位置：

```text
data/raw/ytower_seq_recipes.json
```

實際來源 JSON 共有 **29,597 筆食譜**。欄位為：

```text
SEQ
食譜名稱
上線日期
關鍵字
食譜網址
材料
做法步驟
```

本專案實際掃描後：

- 食譜：29,597 筆
- `SEQ` 重複：0
- 重複食譜名稱：17 組
- 材料列：257,537 列

因此資料庫主鍵不使用「食譜名稱」，而是保留來源的 `SEQ` 作為唯一識別欄位。

### 食品營養成分資料庫

檔案位置：

```text
data/reference/food_nutrition_2025.xlsx
```

來源檔第 1 列註明：**營養數值單位為每 100 g 可食部分之含量**。

因此本專案營養計算使用：

```text
食材營養值 × weight_g / 100
```

---

# 2. 專案資料夾結構

```text
Recipe_Collections_v2/
│
├── .env.example
├── .gitignore
├── .dockerignore
├── docker-compose.yml
├── README.md
│
├── .vscode/
│   ├── extensions.json
│   └── settings.json
│
├── data/
│   ├── raw/
│   │   └── ytower_seq_recipes.json
│   │
│   ├── reference/
│   │   ├── food_nutrition_2025.xlsx
│   │   ├── ingredient_aliases.json
│   │   └── unit_weight_map.json
│   │
│   ├── processed/
│   │   ├── profile_report.json
│   │   ├── recipes_clean.json
│   │   └── recipes_normalized.json
│   │
│   └── manual_review/
│       └── manual_review.json
│
├── mysql/
│   ├── data/
│   └── init/
│       ├── 001_schema.sql
│       ├── 002_seed_units.sql
│       └── 003_views.sql
│
├── python/
│   ├── Dockerfile
│   ├── pyproject.toml
│   │
│   ├── app/
│   │   ├── __init__.py
│   │   ├── api.py
│   │   ├── config.py
│   │   ├── db.py
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── normalization.py
│   │       └── recommendation.py
│   │
│   └── scripts/
│       ├── 01_profile_raw_json.py
│       ├── 02_clean_recipes.py
│       ├── 03_normalize_recipes.py
│       ├── 04_import_recipes_mysql.py
│       ├── 05_import_nutrition_excel.py
│       ├── 06_match_ingredient_nutrition.py
│       ├── 07_export_manual_review.py
│       ├── 08_apply_manual_review.py
│       ├── 09_calculate_recipe_nutrition.py
│       └── 10_pipeline.py
│
└── docs/
    └── er_model.dbml
```

---

# 3. 最終資料處理流程

本版正式流程：

```text
① YTower 原始 JSON
        ↓
② 檢查原始資料
        ↓
③ 材料拆解
        ↓
④ 食材名稱標準化
        ↓
⑤ 數量與單位正規化
        ↓
⑥ 可換算項目計算 weight_g
        ↓
⑦ ER Model 拆表 / MySQL 正規化
        ↓
⑧ ingredient 去重複
        ↓
⑨ 食品營養 Excel 匯入 nutrition_source
        ↓
⑩ ingredient ↔ nutrition_source 名稱 Matching
        ↓
⑪ 無法確定者輸出 manual_review.json
        ↓
⑫ 人工 APPROVED / REJECTED
        ↓
⑬ 建立 ingredient_nutrition_map
        ↓
⑭ MySQL JOIN
        ↓
⑮ Python 計算每項食材營養值
        ↓
⑯ GROUP BY / 彙總整道食譜營養值
        ↓
⑰ Flask API
        ↓
⑱ Hermes 呼叫 Flask API
```

---

# 4. 為什麼不直接把「杯、大匙、顆」全部硬轉成克？

這是這版與較簡化做法最重要的差異。

例如：

```text
水 1大匙
油 1大匙
麵粉 1大匙
糖 1大匙
```

它們都是 `1大匙`，但重量並不相同。

因此本版只把「本身就是質量單位」直接換算成 g：

```text
g       × 1
kg      × 1000
斤      × 600
兩      × 37.5
錢      × 3.75
```

而：

```text
杯
大匙
小匙
顆
個
條
片
塊
朵
盒
包
```

需要「食材 + 單位」專屬重量。

例如之後可以在：

```text
data/reference/unit_weight_map.json
```

加入：

```json
ingredient,unit,grams_per_unit,source,note
雞蛋,顆,50,人工查核,去殼可食部估算
```

然後重新執行正規化即可。

## 適量 / 少許 / 隨意 / 酌量

這類資料**不應假裝有精確重量**。

本版會保留：

```text
raw_amount_text = 適量
quantity_value = NULL
weight_g = NULL
needs_manual_review = 1
```

因此營養計算不會憑空製造假的克數。

---

# 5. 第一次建立：先建立個別 container

以下所有指令都在專案根目錄執行：

```bash
cd Recipe_Collections_v2
```

先建立環境檔：

```bash
cp .env.example .env
```

打開 `.env`，至少修改：

```env
MYSQL_ROOT_PASSWORD=你自己的root密碼
DB_PASSWORD=同一個root密碼
HERMES_API_KEY=你自己設定的API金鑰
```

目前依你的要求，Python 也先使用：

```env
DB_USER=root
```

> 開發環境先用 root 可以；真正部署時建議再另外建立權限較小的 application user。

---

# 6. 建立 Docker network

MySQL 與 Python 是兩個獨立 container。

若要讓：

```text
recipe-python → recipe-mysql
```

可以直接用 container name 溝通，先建立 user-defined bridge network：

```bash
docker network create recipe-net
```

檢查：

```bash
docker network ls
```

應看到：

```text
recipe-net
```

---

# 7. 先單獨建立 MySQL container

## 7.1 啟動 MySQL

```bash
docker run -d \
  --name recipe-mysql \
  --network recipe-net \
  -p 127.0.0.1:3307:3306 \
  -e MYSQL_ROOT_PASSWORD=你的root密碼 \
  -e MYSQL_ROOT_HOST=% \
  -e MYSQL_DATABASE=recipe_ai \
  -v "$PWD/mysql/data:/var/lib/mysql" \
  -v "$PWD/mysql/init:/docker-entrypoint-initdb.d:ro" \
  mysql:8.4
```

## 7.2 為什麼是 `3307:3306`

格式是：

```text
主機port:container port
```

MySQL container 內部標準 port 是：

```text
3306
```

你的 Mac 想用：

```text
3307
```

所以正確是：

```text
3307:3306
```

而不是：

```text
3307:3307
```

## 7.3 `127.0.0.1:3307:3306`

加入 `127.0.0.1` 後代表 MySQL port 只對本機開放。

這比：

```text
0.0.0.0:3307
```

更適合目前的本機開發。

---

# 8. MySQL data volume

使用：

```bash
-v "$PWD/mysql/data:/var/lib/mysql"
```

意思：

```text
Mac 專案/mysql/data
        ↓
container /var/lib/mysql
```

因此刪除 container：

```bash
docker rm recipe-mysql
```

**不會等於刪除資料庫資料**。

只要 `mysql/data` 還在，重建 container 後資料仍可保留。

---

# 9. MySQL init SQL 的執行時機

這個掛載：

```bash
-v "$PWD/mysql/init:/docker-entrypoint-initdb.d:ro"
```

會讓 MySQL **第一次建立空資料目錄**時，自動執行：

```text
001_schema.sql
002_seed_units.sql
003_views.sql
```

注意：如果 `mysql/data` 已經有舊資料，MySQL 不會每次啟動都重新執行 init SQL。

如果你在開發階段想完全重建：

```bash
docker stop recipe-mysql
docker rm recipe-mysql
rm -rf mysql/data/*
touch mysql/data/.gitkeep
```

再重新 `docker run`。

**這會刪除現有資料庫資料，正式資料不要這樣做。**

---

# 10. 檢查 MySQL container

```bash
docker ps
```

查看 log：

```bash
docker logs -f recipe-mysql
```

進入 MySQL：

```bash
docker exec -it recipe-mysql mysql -uroot -p
```

輸入密碼後：

```sql
SHOW DATABASES;
USE recipe_ai;
SHOW TABLES;
```

---

# 11. MySQL Workbench 連線

建立新的 connection：

```text
Connection Name : Recipe AI Docker
Hostname        : 127.0.0.1
Port            : 3307
Username        : root
Password        : 你的 MYSQL_ROOT_PASSWORD
Default Schema  : recipe_ai
```

測試成功後進入。

常用檢查：

```sql
USE recipe_ai;

SHOW TABLES;

SELECT COUNT(*) FROM recipes;
SELECT COUNT(*) FROM ingredients;
SELECT COUNT(*) FROM recipe_ingredients;
SELECT COUNT(*) FROM nutrition_source;
```

---

# 12. 單獨建立 Python image

在專案根目錄：

```bash
docker build -t recipe-python:dev ./python
```

Dockerfile 基底：

```dockerfile
FROM python:3.13-slim
```

然後安裝：

```text
uv
Chromium
Chromium Driver
```

Chromium 是為了保留你目前 Selenium / webdriver-manager 的使用空間。

---

# 13. uv 的角色

`python/pyproject.toml` 中已放入你指定的套件：

```toml
dependencies = [
    "beautifulsoup4>=4.14.3",
    "curl-cffi>=0.15.0",
    "cryptography>=46.0.0",
    "flask>=3.1.3",
    "kaggle>=1.8.3",
    "matplotlib>=3.10.8",
    "numpy!=2.4.0",
    "openpyxl>=3.1.5",
    "pandas>=2.3.3",
    "pymongo>=4.16.0",
    "pymysql>=1.2.0",
    "python-dateutil>=2.9.0.post0",
    "requests>=2.32.5",
    "seaborn>=0.13.2",
    "selenium>=4.39.0",
    "webdriver-manager>=4.0.2",
    "yfinance>=1.0",
]
```

> 補充：`cryptography` 是本版額外加入的連線相依套件，用來避免 MySQL 8.4 `caching_sha2_password` 搭配 PyMySQL 時遇到 RSA 驗證問題。你指定的套件全部保留。

Docker image 建置時執行：

```bash
uv sync --no-dev
```

虛擬環境固定放在：

```text
/opt/venv
```

這樣即使 VS Code 把本機專案 mount 進 `/workspace`，也不會蓋掉 container 中的 Python virtual environment。

---

# 14. 單獨啟動 Python container

先確認 MySQL container 已經執行。

```bash
docker ps
```

啟動 Python：

```bash
docker run -d \
  --name recipe-python \
  --network recipe-net \
  -p 127.0.0.1:5001:5000 \
  -e DB_HOST=recipe-mysql \
  -e DB_PORT=3306 \
  -e DB_NAME=recipe_ai \
  -e DB_USER=root \
  -e DB_PASSWORD=你的root密碼 \
  -e HERMES_API_KEY=你的API金鑰 \
  -e PYTHONPATH=/workspace/python \
  -e UV_PROJECT_ENVIRONMENT=/opt/venv \
  -v "$PWD:/workspace" \
  -w /workspace/python \
  recipe-python:dev \
  uv run flask --app app.api:app run --host=0.0.0.0 --port=5000 --reload
```

這裡 Flask 使用：

```text
Mac 5001 → container 5000
```

特別使用 5001，是為了避免你的電腦上原本已有 5000 port 被占用。

---

# 15. Python container 為什麼連 `recipe-mysql:3306`

在 Docker network 裡：

```text
recipe-python
    │
    └── recipe-mysql:3306
```

Python **不是**使用：

```text
localhost:3307
```

因為 container 裡的 `localhost` 代表 Python container 自己。

所以：

```env
DB_HOST=recipe-mysql
DB_PORT=3306
```

Workbench 是從 Mac 連入 Docker，因此才是：

```text
127.0.0.1:3307
```

兩者不要混淆。

---

# 16. VS Code 連線 Python container

建議安裝 VS Code extension：

```text
Python
Docker
Dev Containers
```

本專案 `.vscode/extensions.json` 已列出建議 extension。

## 操作

1. 開啟 VS Code。
2. 開啟 `Recipe_Collections_v2` 資料夾。
3. `Command + Shift + P`。
4. 搜尋：

```text
Dev Containers: Attach to Running Container...
```

5. 選：

```text
recipe-python
```

6. 進 container 後開啟：

```text
/workspace
```

Python interpreter 使用：

```text
/opt/venv/bin/python
```

---

# 17. 在 container 確認 uv

VS Code container terminal：

```bash
cd /workspace/python
uv --version
uv pip list
```

執行 Python：

```bash
uv run python --version
```

執行 Flask：

```bash
uv run flask --app app.api:app run --host=0.0.0.0 --port=5000
```

---

# 18. 個別 container 確認完成後改用 Compose

先停止並移除兩個「個別測試 container」：

```bash
docker stop recipe-python recipe-mysql
docker rm recipe-python recipe-mysql
```

資料仍保存在：

```text
mysql/data
```

所以 MySQL 資料不會因為 container 被刪除就消失。

---

# 19. Docker Compose 啟動

確認 `.env` 已完成：

```bash
cp .env.example .env
```

然後：

```bash
docker compose up -d --build
```

檢查：

```bash
docker compose ps
```

應看到：

```text
recipe-mysql
recipe-python
```

---

# 20. Compose 常用指令

啟動：

```bash
docker compose up -d
```

停止：

```bash
docker compose stop
```

停止並刪 container/network：

```bash
docker compose down
```

重新 build Python：

```bash
docker compose up -d --build python
```

查看 MySQL log：

```bash
docker compose logs -f mysql
```

查看 Python log：

```bash
docker compose logs -f python
```

進 Python container：

```bash
docker compose exec python bash
```

進 MySQL：

```bash
docker compose exec mysql mysql -uroot -p
```

---

# 21. 資料清洗程式：01_profile_raw_json.py

位置：

```text
python/scripts/01_profile_raw_json.py
```

功能：

- 確認食譜筆數。
- 確認欄位。
- 檢查重複 `SEQ`。
- 檢查重複食譜名稱。
- 統計材料總列數。
- 統計「適量、少許、隨意、酌量」等不確定用量。
- 統計常見關鍵字。

執行：

```bash
docker compose exec python \
  uv run python scripts/01_profile_raw_json.py
```

輸出：

```text
data/processed/profile_report.json
```

---

# 22. 資料清洗程式：02_clean_recipes.py

位置：

```text
python/scripts/02_clean_recipes.py
```

## 主要處理

### 22.1 欄位改為程式使用名稱

例如：

```text
SEQ        → seq
食譜名稱    → name
上線日期    → published_date
關鍵字      → keywords
食譜網址    → source_url
做法步驟    → steps
```

### 22.2 日期標準化

例如：

```text
2006-1-1
```

轉為：

```text
2006-01-01
```

### 22.3 關鍵字拆成 list

原始：

```text
主菜, 牛肉, 中式料理, 葷食, 乾貨
```

清洗後：

```json
["主菜", "牛肉", "中式料理", "葷食", "乾貨"]
```

### 22.4 材料拆列

原始：

```text
牛肉 約1/2斤 | 鮮百合 2∼3顆 | 蓮子 20顆
```

轉為：

```json
[
  {"line_no": 1, "raw_text": "牛肉 約1/2斤"},
  {"line_no": 2, "raw_text": "鮮百合 2~3顆"},
  {"line_no": 3, "raw_text": "蓮子 20顆"}
]
```

執行：

```bash
docker compose exec python \
  uv run python scripts/02_clean_recipes.py
```

輸出：

```text
data/processed/recipes_clean.json
```

使用 JSON 而不是把 29,597 筆全部重新包在巨大 JSON array 中，方便逐筆 ETL。

---

# 23. 核心正規化：normalization.py

位置：

```text
python/app/services/normalization.py
```

這是整個清洗流程最重要的共用模組。

## 23.1 NFKC 正規化

使用：

```python
unicodedata.normalize("NFKC", text)
```

可以統一：

```text
全形數字
全形英文字
部分特殊符號
```

例如：

```text
Ａ1醬
```

會轉成：

```text
A1醬
```

## 23.2 範圍符號統一

```text
2∼3
2～3
```

統一成：

```text
2~3
```

## 23.3 同義詞字典

位置：

```text
data/reference/ingredient_aliases.json
```

範例：

```json
alias,canonical
蕃茄,番茄
蒜頭,大蒜
金茸,金針菇
```

你之後只需要維護這個 JSON，不需要一直改 Python 程式。

---

# 24. 03_normalize_recipes.py

執行：

```bash
docker compose exec python \
  uv run python scripts/03_normalize_recipes.py
```

輸出：

```text
data/processed/recipes_normalized.json
```

實際使用目前來源 JSON 執行後：

```text
recipes:            29,597
ingredient rows:   257,537
known weight rows:  89,801
manual review rows:167,736
```

`manual review rows` 很高不是程式失敗，而是來源中大量使用：

```text
顆
片
個
大匙
小匙
杯
少許
適量
```

這些不能安全直接當成克數。

---

# 25. 正規化後單一材料資料結構

例如：

```text
牛肉 約1/2斤
```

會變成類似：

```json
{
  "raw_text": "牛肉 約1/2斤",
  "raw_name": "牛肉",
  "canonical_name": "牛肉",
  "raw_amount_text": "約1/2斤",
  "quantity_min": 0.5,
  "quantity_max": 0.5,
  "quantity_value": 0.5,
  "canonical_unit": "斤",
  "weight_g": 300.0,
  "is_estimated": true,
  "needs_manual_review": false,
  "review_reason": null
}
```

因為台灣：

```text
1斤 = 600g
```

所以：

```text
0.5 × 600 = 300g
```

---

# 26. MySQL 正規化

執行：

```bash
docker compose exec python \
  uv run python scripts/04_import_recipes_mysql.py
```

主要拆表：

```text
recipes
keywords
recipe_keywords
ingredients
ingredient_aliases
units
recipe_ingredients
```

## 為什麼 ingredients 要獨立？

如果 20,000 道食譜都出現：

```text
番茄
```

不需要重複建立 20,000 個「番茄主資料」。

只建立：

```text
ingredients.id = 123
canonical_name = 番茄
```

所有食譜透過 `recipe_ingredients.ingredient_id` 指向它。

這就是正規化後的關聯式設計。

---

# 27. nutrition_source 匯入

執行：

```bash
docker compose exec python \
  uv run python scripts/05_import_nutrition_excel.py
```

程式使用 Excel：

```text
data/reference/food_nutrition_2025.xlsx
```

## 為什麼 nutrition_source 同時有欄位與 raw_data JSON？

食品營養 Excel 有非常多欄位。

系統常用欄位會直接建立 column，例如：

```text
energy_kcal
protein_g
fat_g
carbohydrate_g
dietary_fiber_g
sodium_mg
potassium_mg
calcium_mg
magnesium_mg
iron_mg
zinc_mg
phosphorus_mg
vitamin_c_mg
...
```

但為了「整份來源資料不丟失」，原始 Excel 該列所有欄位仍會存到：

```text
nutrition_source.raw_data
```

這樣兼顧：

```text
查詢速度 + 原始資料完整性
```

---

# 28. 食材名稱 Matching

執行：

```bash
docker compose exec python \
  uv run python scripts/06_match_ingredient_nutrition.py
```

流程：

```text
ingredients.canonical_name
       ↓
清理名稱
       ↓
nutrition_source.sample_name
nutrition_source.common_name
       ↓
精確 / 包含 / SequenceMatcher similarity
       ↓
score >= 0.90
       ├─ YES → ingredient_nutrition_map
       └─ NO
           ↓
       score >= 0.72
           ├─ YES → manual_review
           └─ NO  → 保留未匹配
```

這一段故意不把低相似度強行配對。

因為：

```text
配錯營養資料
```

比：

```text
暫時沒有營養資料
```

更危險。

---

# 29. 匯出人工審查

```bash
docker compose exec python \
  uv run python scripts/07_export_manual_review.py
```

會產生：

```text
data/manual_review/manual_review.json
```

主要欄位：

```text
review_id
ingredient_id
ingredient_name
candidate_nutrition_id
candidate_name
score
status
decision
note
```

你只需要在 `decision` 填：

```text
APPROVED
```

或：

```text
REJECTED
```

---

# 30. 套用人工審查

```bash
docker compose exec python \
  uv run python scripts/08_apply_manual_review.py
```

若 `APPROVED`：

```text
ingredient_nutrition_map
```

會正式建立對應。

同一個 ingredient 其他 pending candidate 會改為 rejected。

---

# 31. 計算整道食譜營養

執行：

```bash
docker compose exec python \
  uv run python scripts/09_calculate_recipe_nutrition.py
```

公式：

```text
單一食材營養值
=
食品營養資料庫每100g營養值
×
食譜中的 weight_g
÷
100
```

例如：

```text
牛肉 300g
營養資料：每100g 250 kcal
```

則：

```text
250 × 300 / 100
= 750 kcal
```

所有可以計算的材料再加總到：

```text
recipe_nutrition_summary
```

---

# 32. coverage_percent 很重要

不是每一列食材都有 `weight_g`。

所以 API 不應只顯示：

```text
熱量 = 500 kcal
```

還應顯示：

```text
nutrition_coverage_percent = 70%
```

它表示目前有多少材料列真正完成：

```text
weight_g + nutrition mapping
```

因此使用者知道營養值的完整程度。

---

# 33. 一次跑 ETL

可以執行：

```bash
docker compose exec python \
  uv run python scripts/10_pipeline.py
```

它會依序執行：

```text
01 → 02 → 03 → 04 → 05 → 06 → 07
```

然後停止。

因為第 08 階段必須先人工審查，所以不應自動跳過。

完成 `manual_review.json` 後：

```bash
docker compose exec python \
  uv run python scripts/08_apply_manual_review.py


docker compose exec python \
  uv run python scripts/09_calculate_recipe_nutrition.py
```

---

# 34. Flask API 架構

主程式：

```text
python/app/api.py
```

DB 連線：

```text
python/app/db.py
```

設定：

```text
python/app/config.py
```

推薦邏輯：

```text
python/app/services/recommendation.py
```

---

# 35. Flask API 測試

Compose 啟動後：

```bash
curl http://127.0.0.1:5001/health
```

成功：

```json
{
  "status": "ok",
  "mysql": true
}
```

---

# 36. 查詢單一食譜

```bash
curl http://127.0.0.1:5001/api/v1/recipes/A01-002
```

會取得：

```text
食譜基本資料
材料
正規化材料名稱
單位
weight_g
營養摘要
```

---

# 37. 搜尋食譜

```bash
curl "http://127.0.0.1:5001/api/v1/recipes/search?q=牛肉&limit=10"
```

可以用：

```text
食譜名稱
食材名稱
```

查詢。

---

# 38. 食材推薦 API

```bash
curl -X POST \
  http://127.0.0.1:5001/api/v1/recommend \
  -H 'Content-Type: application/json' \
  -d '{
    "ingredients": ["番茄", "牛肉", "洋蔥"],
    "limit": 5
  }'
```

推薦服務目前使用：

```text
requested_coverage
+
Jaccard similarity
```

概念：

```text
使用者食材集合 A
食譜食材集合 B

J(A,B) = |A ∩ B| / |A ∪ B|
```

---

# 39. Hermes API

Hermes 使用專用 endpoint：

```text
POST /api/v1/hermes/recommend
```

必須帶：

```text
X-API-Key
```

測試：

```bash
curl -X POST \
  http://127.0.0.1:5001/api/v1/hermes/recommend \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: 你的HERMES_API_KEY' \
  -d '{
    "ingredients": ["番茄", "蛋", "洋蔥"],
    "limit": 5
  }'
```

---

# 40. Hermes OpenAPI

API 提供：

```text
http://127.0.0.1:5001/openapi.json
```

若你的 Hermes 版本支援 OpenAPI tool，可以把這份 OpenAPI schema 提供給 Hermes。

Hermes 要呼叫的工具語意可以設定為：

```text
Tool name:
recipe_recommendation

Description:
根據使用者目前可用食材推薦食譜。

Input:
ingredients: string[]
limit: integer

HTTP:
POST /api/v1/hermes/recommend

Header:
X-API-Key: <HERMES_API_KEY>
```

---

# 41. 如果 Hermes 不在你的 Mac 本機

`127.0.0.1:5001` 只能從你的 Mac 存取。

如果 Hermes 在外部 server，需要把 Flask API 暴露成 HTTPS public URL。

例如你原本使用 ngrok 時，可把：

```text
localhost:5001
```

建立 HTTPS tunnel。

之後 Hermes URL 改成：

```text
https://你的公開網址/api/v1/hermes/recommend
```

不要把 MySQL `3307` 暴露到公網；只暴露 Flask API。

---

# 42. MySQL Workbench 建議檢查 SQL

## 食譜筆數

```sql
SELECT COUNT(*) AS recipe_count
FROM recipes;
```

## 去重後食材

```sql
SELECT COUNT(*) AS ingredient_count
FROM ingredients;
```

## 材料筆數

```sql
SELECT COUNT(*) AS recipe_ingredient_count
FROM recipe_ingredients;
```

## 尚需處理的重量

```sql
SELECT
    COUNT(*) AS total_rows,
    SUM(weight_g IS NOT NULL) AS known_weight_rows,
    SUM(needs_manual_review = 1) AS review_rows
FROM recipe_ingredients;
```

## 看哪些單位最需要補換算表

```sql
SELECT
    u.canonical_unit,
    COUNT(*) AS cnt
FROM recipe_ingredients ri
JOIN units u ON u.id = ri.unit_id
WHERE ri.weight_g IS NULL
GROUP BY u.canonical_unit
ORDER BY cnt DESC;
```

## 尚未匹配營養資料的食材

```sql
SELECT
    i.id,
    i.canonical_name
FROM ingredients i
LEFT JOIN ingredient_nutrition_map m
    ON m.ingredient_id = i.id
WHERE m.ingredient_id IS NULL
ORDER BY i.canonical_name;
```

## 查看整道食譜熱量

```sql
SELECT
    r.seq,
    r.name,
    n.energy_kcal,
    n.coverage_percent
FROM recipes r
LEFT JOIN recipe_nutrition_summary n
    ON n.recipe_id = r.id
ORDER BY n.energy_kcal DESC;
```

---

# 43. ER Model

檔案：

```text
docs/er_model.dbml
```

使用方式：

1. 開啟 dbdiagram.io。
2. 建立 New Diagram。
3. 把 `docs/er_model.dbml` 全部內容貼入左側 DBML editor。
4. 右側會自動產生 ER Model。

主要關係：

```text
recipes 1 ── N recipe_ingredients N ── 1 ingredients

recipes N ── N keywords

ingredients 1 ── N ingredient_aliases

ingredients 1 ── N ingredient_unit_weights N ── 1 units

ingredients 1 ── 1 ingredient_nutrition_map N ── 1 nutrition_source

ingredients 1 ── N manual_review N ── 1 nutrition_source

recipes 1 ── 1 recipe_nutrition_summary
```

---

# 44. 完整第一次執行順序

## A. 準備

```bash
cd Recipe_Collections_v2
cp .env.example .env
```

修改 `.env`。

## B. Compose 建立環境

```bash
docker compose up -d --build
```

## C. 查看服務

```bash
docker compose ps
```

## D. 原始資料分析

```bash
docker compose exec python uv run python scripts/01_profile_raw_json.py
```

## E. 清洗

```bash
docker compose exec python uv run python scripts/02_clean_recipes.py
```

## F. 正規化

```bash
docker compose exec python uv run python scripts/03_normalize_recipes.py
```

## G. 食譜入 MySQL

```bash
docker compose exec python uv run python scripts/04_import_recipes_mysql.py
```

## H. 營養資料入 MySQL

```bash
docker compose exec python uv run python scripts/05_import_nutrition_excel.py
```

## I. 自動 Matching

```bash
docker compose exec python uv run python scripts/06_match_ingredient_nutrition.py
```

## J. 匯出人工審核

```bash
docker compose exec python uv run python scripts/07_export_manual_review.py
```

## K. 編輯

```text
data/manual_review/manual_review.json
```

填入：

```text
APPROVED / REJECTED
```

## L. 套用人工審核

```bash
docker compose exec python uv run python scripts/08_apply_manual_review.py
```

## M. 計算營養

```bash
docker compose exec python uv run python scripts/09_calculate_recipe_nutrition.py
```

## N. API 測試

```bash
curl http://127.0.0.1:5001/health
```

---

# 45. 本版相對上一版的主要修正

### 修正 1：先個別 container，再 Compose

不直接從 Compose 開始。

先理解：

```text
MySQL container
Python container
Docker network
port mapping
volume
```

全部正常後才改為 Compose。

### 修正 2：MySQL port

固定使用：

```text
Mac:       3307
container: 3306
```

即：

```text
3307:3306
```

### 修正 3：Python 使用 uv

套件統一寫入：

```text
python/pyproject.toml
```

不建立另一套互相衝突的 `requirements.txt`。

### 修正 4：Flask port

Mac 使用：

```text
5001
```

container 使用：

```text
5000
```

避免你之前遇到 host port 5000 已被占用。

### 修正 5：清洗與正規化改成真正可執行 pipeline

不只寫概念流程，而是拆成：

```text
01～10 scripts
```

每一階段可以單獨執行與檢查。

### 修正 6：保留 raw value

不管最後正規化結果如何，都保留：

```text
raw_text
raw_name
raw_amount_text
```

之後可以追溯原始資料。

### 修正 7：不把適量/少許硬算重量

這類資料會標：

```text
needs_manual_review = 1
```

### 修正 8：食品營養資料完整保留

除了抽取常用營養欄位，也把整列存入：

```text
nutrition_source.raw_data
```

### 修正 9：加入營養匹配人工流程

```text
自動匹配
→ manual_review
→ APPROVED/REJECTED
→ ingredient_nutrition_map
```

避免 fuzzy matching 直接污染正式資料。

### 修正 10：Flask 專門提供 Hermes endpoint

```text
/api/v1/hermes/recommend
```

並提供：

```text
/openapi.json
```

---

# 46. 下一步建議執行順序

第一次不要直接全部跑完。

建議照這個順序練習：

```text
第 1 次：只建立 MySQL container + Workbench
第 2 次：只建立 Python container + VS Code
第 3 次：測試 recipe-python → recipe-mysql
第 4 次：改用 Compose
第 5 次：跑 01 profile
第 6 次：跑 02 clean
第 7 次：打開 recipes_clean.json 看資料
第 8 次：跑 03 normalize
第 9 次：打開 recipes_normalized.json 看 weight_g
第10 次：匯入 recipes MySQL
第11 次：匯入 nutrition
第12 次：做 Matching
第13 次：人工 Review
第14 次：計算營養
第15 次：啟動 Flask
第16 次：Hermes 串接
```

這樣每一步出錯時，可以知道錯誤是在哪一層，而不是同時除錯 Docker、MySQL、Python、ETL、API。

## 食材 + 單位 → grams_per_unit 對照表

新版已加入從 YTower 原始 JSON 自動擷取「數量單位 ↔ 明示重量」的流程。

執行：

```bash
docker compose exec python uv run python scripts/03a_build_unit_weight_map.py
```

會產生：

- `data/reference/unit_weight_map.json`：可直接套用的 ACTIVE 對照。
- `data/reference/unit_weight_candidates.json`：包含 ACTIVE 與需要人工確認的 REVIEW 候選。
- `data/reference/unit_weight_pending_top500.json`：來源 JSON 中高頻但尚未建立克重的食材+單位組合，供人工優先補值。

例如來源有：

```text
鮮香菇 8朵(約120公克)
```

則建立：

```text
鮮香菇,朵,15
```

`03_normalize_recipes.py` 讀取 `unit_weight_map.json` 後，可將：

```text
鮮香菇 4朵
```

估算為：

```text
weight_g = 60
```

注意：`杯 / 大匙 / 小匙 / cc / ml` 是體積單位。除非來源資料明示該食材的重量對照，或另有可信的密度資料，不應直接把所有食材假設成 `1 ml = 1 g`。

---

# 新增：食材密度 `ingredient + density_g_ml`

為了讓 `ml / cc / L / 杯 / 大匙 / 小匙 / 茶匙` 等體積單位可以轉成 `weight_g`，專案新增食材密度對照。

## 參考檔

```text
data/reference/ingredient_density_map.json
```

欄位：

```text
ingredient,density_g_ml,density_type,confidence,status,source,note
```

其中 `density_g_ml` 表示每 1 ml 約重多少克。

例如：

```text
醬油 density_g_ml = 1.16
```

若食譜材料是：

```text
醬油 2大匙
```

因為：

```text
1大匙 = 15 ml
2大匙 = 30 ml
```

所以：

```text
weight_g = 30 × 1.16 = 34.8 g
```

`03_normalize_recipes.py` 現在會依下列優先順序計算重量：

```text
1. 原本就是 g/kg/斤/兩/錢
2. ingredient + unit → grams_per_unit
3. 體積單位 → ml × ingredient density_g_ml
4. 仍無法換算 → weight_g = NULL，進 manual review
```

### ACTIVE / REVIEW

只有 `status=ACTIVE` 的密度會自動套用。

`REVIEW` 表示品牌、濃度、顆粒度或壓實程度造成差異較大，例如美乃滋、花生醬、可可粉等，不會自動套用。

粉類的 `density_g_ml` 是廚房量杯使用的 **bulk density（鬆裝體積密度）**，不是材料本身的真密度，所以仍視為估算值。

## MySQL 新表

```text
ingredient_densities
```

與：

```text
ingredients 1 ── 1 ingredient_densities
```

關聯。

在 `04_import_recipes_mysql.py` 完成後執行：

```bash
docker compose exec python \
  uv run python scripts/04a_import_reference_maps.py
```

它會把：

```text
unit_weight_map.json
ingredient_density_map.json
```

同步寫入：

```text
ingredient_unit_weights
ingredient_densities
```

完整 pipeline `10_pipeline.py` 也已加入此步驟。
