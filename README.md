# Recipe Collections - Airflow + Kafka + MongoDB + MySQL

## 目標資料流

Airflow
→ YTower crawler
→ Kafka topic `ytower-recipes`
→ `recipe-kafka-to-mongodb`
→ MongoDB `recipe_ai.raw_recipes`
→ Python ETL
→ MySQL `recipe_ai`
→ Flask API
→ Hermes / LINE Bot

## 第一次啟動

```bash
cp .env.example .env
docker compose up -d --build
docker compose ps
```

## 先用現有 JSON 建立 MongoDB

把舊資料放到：

```text
data/raw/ytower_seq_recipes.json
```

執行：

```bash
docker compose exec python bash
cd /workspace/python
uv run python scripts/00_seed_mongodb_from_json.py
```

檢查：

```bash
docker exec -it recipe-mongodb mongosh -u root -p rootpassword --authenticationDatabase admin
```

Mongo shell：

```javascript
use recipe_ai
db.raw_recipes.countDocuments()
db.raw_recipes.find({}, {_id:0,SEQ:1,食譜名稱:1}).limit(3)
```

## 執行 ETL

```bash
docker compose exec python bash
cd /workspace/python
uv run python scripts/10_pipeline.py
```

Pipeline 會停在 manual review。

完成 `data/manual_review/manual_review.json` 後：

```bash
uv run python scripts/08_apply_manual_review.py
uv run python scripts/09_calculate_recipe_nutrition.py
```

## Kafka topic

建立：

```bash
docker exec -it recipe-kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --create --if-not-exists --topic ytower-recipes --partitions 1 --replication-factor 1
```

查看：

```bash
docker exec -it recipe-kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list
```

## Airflow

瀏覽器：

```text
http://localhost:8080
```

第一次建議先讓 DAG 維持 `schedule=None`，手動 Trigger。

## 爬蟲整合

`crawler/ytower_crawler.py` 不猜測你原本的 selector。
請把你已驗證可用的 YTower 爬蟲主函式搬入 `crawl_recipes()`，
回傳 `list[dict]`。

Airflow 會呼叫：

```text
crawl_and_publish()
```

並將每筆 recipe 發送到 Kafka。

## API

```bash
curl http://localhost:5001/health
curl "http://localhost:5001/api/v1/recipes/search?q=牛肉"
```

## 容器角色

- recipe-airflow：排程
- recipe-postgres：Airflow metadata
- recipe-kafka：message broker
- recipe-kafka-to-mongodb：Kafka consumer
- recipe-mongodb：raw recipe storage
- recipe-python：ETL + Flask API
- recipe-mysql：normalized production database

## 注意

這份整合版是完整可啟動骨架，但 `crawler/ytower_crawler.py`
需要放入你目前已經驗證的實際爬蟲邏輯。這是刻意保留，
因為目前沒有你舊爬蟲的完整 source code，不應猜測網站 selector。
