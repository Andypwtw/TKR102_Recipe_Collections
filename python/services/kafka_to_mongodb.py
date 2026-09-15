from __future__ import annotations
import json, os
from datetime import datetime, timezone
from kafka import KafkaConsumer
from pymongo import MongoClient

def main():
    consumer=KafkaConsumer(
        os.getenv("KAFKA_TOPIC","ytower-recipes"),
        bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS","kafka:9092"),
        group_id="recipe-mongodb-writer",
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        value_deserializer=lambda b: json.loads(b.decode("utf-8")),
    )
    client=MongoClient(os.getenv(
        "MONGO_URI",
        "mongodb://root:rootpassword@mongodb:27017/recipe_ai?authSource=admin"
    ))
    col=client[os.getenv("MONGO_DATABASE","recipe_ai")][os.getenv("MONGO_COLLECTION","raw_recipes")]
    col.create_index("SEQ", unique=True)
    print("Kafka -> MongoDB consumer started")
    for msg in consumer:
        recipe=msg.value
        seq=recipe.get("SEQ")
        if not seq:
            print("skip message without SEQ")
            continue
        recipe["source"]="ytower"
        recipe["ingested_at"]=datetime.now(timezone.utc)
        col.update_one({"SEQ":seq},{"$set":recipe},upsert=True)
        print(f"upserted {seq}")

if __name__ == "__main__":
    main()
