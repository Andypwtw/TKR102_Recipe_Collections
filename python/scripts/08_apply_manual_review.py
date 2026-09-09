from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import sys

PYTHON_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = PYTHON_DIR.parent
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))

from app.db import get_connection


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply manual nutrition matching decisions from JSON.")
    parser.add_argument("--input", type=Path, default=PROJECT_ROOT / "data" / "manual_review" / "manual_review.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    approved = 0
    rejected = 0
    rows = json.loads(args.input.read_text(encoding="utf-8"))
    with get_connection() as conn, conn.cursor() as cursor:
        for row in rows:
            decision = (row.get("decision") or "").strip().upper()
            if decision not in {"APPROVED", "REJECTED"}:
                continue
            review_id = int(row["review_id"])
            ingredient_id = int(row["ingredient_id"])
            nutrition_id = int(row["candidate_nutrition_id"])
            note = (row.get("note") or "").strip() or None

            cursor.execute(
                "UPDATE manual_review SET status=%s, note=%s, reviewed_at=%s WHERE id=%s",
                (decision, note, datetime.now(), review_id),
            )
            if decision == "APPROVED":
                cursor.execute(
                    """
                    INSERT INTO ingredient_nutrition_map
                        (ingredient_id, nutrition_source_id, match_method, match_score, status, reviewed_at)
                    VALUES (%s, %s, 'manual_review', 1, 'MANUAL', %s)
                    ON DUPLICATE KEY UPDATE
                        nutrition_source_id=VALUES(nutrition_source_id),
                        match_method='manual_review', match_score=1, status='MANUAL', reviewed_at=VALUES(reviewed_at)
                    """,
                    (ingredient_id, nutrition_id, datetime.now()),
                )
                cursor.execute(
                    "UPDATE manual_review SET status='REJECTED', reviewed_at=%s WHERE ingredient_id=%s AND id<>%s AND status='PENDING'",
                    (datetime.now(), ingredient_id, review_id),
                )
                approved += 1
            else:
                rejected += 1

    print(f"approved: {approved}, rejected: {rejected}")


if __name__ == "__main__":
    main()
