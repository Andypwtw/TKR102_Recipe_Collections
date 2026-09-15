from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from kafka import KafkaConsumer
from pymongo import MongoClient


def main():
    topic = os.getenv("KAFKA_TOPIC", "ytower-recipes")
    bootstrap = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")

    consumer = KafkaConsumer(
        topic,
        bootstrap_servers=bootstrap,
        group_id="recipe-mongodb-writer",
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        value_deserializer=lambda b: json.loads(b.decode("utf-8")),
    )

    client = MongoClient(
        os.getenv(
            "MONGO_URI",
            "mongodb://root:rootpassword@mongodb:27017/recipe_ai?authSource=admin",
        )
    )

    collection = client[
        os.getenv("MONGO_DATABASE", "recipe_ai")
    ][
        os.getenv("MONGO_COLLECTION", "raw_recipes")
    ]

    collection.create_index("SEQ", unique=True)

    print(f"Kafka -> MongoDB consumer started. topic={topic}")

    for message in consumer:
        recipe = message.value
        seq = recipe.get("SEQ")

        if not seq:
            print("skip message without SEQ")
            consumer.commit()
            continue

        recipe["source"] = "ytower"
        recipe["ingested_at"] = datetime.now(timezone.utc)

        # MongoDB 寫入成功後，才提交 Kafka offset。
        collection.update_one(
            {"SEQ": seq},
            {"$set": recipe},
            upsert=True,
        )

        consumer.commit()

        print(
            f"upserted seq={seq} "
            f"partition={message.partition} "
            f"offset={message.offset}"
        )


if __name__ == "__main__":
    main()
