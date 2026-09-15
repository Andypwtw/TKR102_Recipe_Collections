from __future__ import annotations

import os
from datetime import datetime

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.sensors.python import PythonSensor
from kafka import KafkaConsumer, TopicPartition


def run_crawler():
    from crawler.ytower_crawler import crawl_and_publish
    crawl_and_publish()


def kafka_mongodb_is_synced():
    topic = os.getenv("KAFKA_TOPIC", "ytower-recipes")
    bootstrap = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")

    consumer = KafkaConsumer(
        bootstrap_servers=bootstrap,
        group_id="recipe-mongodb-writer",
        enable_auto_commit=False,
    )

    try:
        partitions = consumer.partitions_for_topic(topic)

        if not partitions:
            print(f"Kafka topic not ready: {topic}")
            return False

        topic_partitions = [
            TopicPartition(topic, partition)
            for partition in sorted(partitions)
        ]

        consumer.assign(topic_partitions)
        end_offsets = consumer.end_offsets(topic_partitions)

        total_lag = 0

        for tp in topic_partitions:
            committed = consumer.committed(tp)
            if committed is None:
                committed = 0

            end = end_offsets[tp]
            lag = max(end - committed, 0)
            total_lag += lag

            print(
                f"{tp.topic}[{tp.partition}] "
                f"committed={committed}, end={end}, lag={lag}"
            )

        print(f"Total Kafka lag: {total_lag}")
        return total_lag == 0

    finally:
        consumer.close()


def check_pipeline_result():
    # Airflow container 已 mount /workspace/python，直接使用專案 DB helper。
    from app.db import get_connection

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) AS cnt FROM recipe_nutrition_summary"
        )
        row = cur.fetchone()

    count = int(row["cnt"])

    if count <= 0:
        raise RuntimeError(
            "recipe_nutrition_summary is empty after pipeline."
        )

    print(
        f"Full automatic pipeline OK. "
        f"recipe_nutrition_summary rows={count}"
    )


with DAG(
    dag_id="recipe_full_pipeline",
    description=(
        "YTower crawler -> Kafka -> MongoDB -> "
        "Recipe ETL 01~09 with automatic nutrition review"
    ),
    start_date=datetime(2026, 9, 1),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    tags=[
        "recipe",
        "crawler",
        "kafka",
        "mongodb",
        "mysql",
        "etl",
        "auto-review",
    ],
) as dag:

    crawl_task = PythonOperator(
        task_id="crawl_ytower",
        python_callable=run_crawler,
    )

    wait_task = PythonSensor(
        task_id="wait_kafka_to_mongodb",
        python_callable=kafka_mongodb_is_synced,
        poke_interval=10,
        timeout=1800,
        mode="reschedule",
    )

    pipeline_task = BashOperator(
        task_id="run_full_recipe_pipeline",
        bash_command=(
            "cd /workspace/python && "
            "python scripts/10_pipeline.py"
        ),
    )

    check_task = PythonOperator(
        task_id="check_nutrition_summary",
        python_callable=check_pipeline_result,
    )

    crawl_task >> wait_task >> pipeline_task >> check_task
