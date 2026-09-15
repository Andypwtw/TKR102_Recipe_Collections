from __future__ import annotations

def crawl_recipes():
    """
    請把你目前已經可正常使用的 YTower 爬蟲主邏輯搬到這裡。
    回傳格式必須為 list[dict]，每筆至少保留：
    SEQ、食譜名稱、上線日期、關鍵字、食譜網址、材料、做法步驟。

    這個整合版刻意不猜測你舊爬蟲的 CSS selector，
    避免破壞你原本已驗證的爬取邏輯。
    """
    raise NotImplementedError(
        "請把現有 YTower crawler 的 crawl_recipes() 邏輯搬入 crawler/ytower_crawler.py"
    )

def crawl_and_publish():
    from crawler.kafka_producer import create_producer, publish_recipe
    producer=create_producer()
    rows=crawl_recipes()
    count=0
    for recipe in rows:
        publish_recipe(producer,recipe)
        count += 1
    producer.flush()
    print(f"crawler published={count}")
