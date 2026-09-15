from __future__ import annotations
import json, os
from kafka import KafkaProducer

def create_producer():
    return KafkaProducer(
        bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS","kafka:9092"),
        key_serializer=lambda s: s.encode("utf-8"),
        value_serializer=lambda obj: json.dumps(obj,ensure_ascii=False).encode("utf-8"),
        acks="all",
    )

def publish_recipe(producer, recipe: dict):
    seq=recipe.get("SEQ")
    if not seq:
        raise ValueError("recipe missing SEQ")
    producer.send(os.getenv("KAFKA_TOPIC","ytower-recipes"),key=seq,value=recipe)
