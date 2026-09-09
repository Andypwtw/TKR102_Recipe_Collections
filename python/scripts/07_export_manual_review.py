from __future__ import annotations

import argparse
import json
from pathlib import Path

import sys

PYTHON_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = PYTHON_DIR.parent
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))

from app.db import get_connection


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export pending nutrition matches for manual review.")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "data" / "manual_review" / "manual_review.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with get_connection() as conn, conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                mr.id AS review_id,
                i.id AS ingredient_id,
                i.canonical_name AS ingredient_name,
                mr.candidate_nutrition_id,
                mr.candidate_name,
                mr.score,
                mr.status,
                '' AS decision,
                '' AS note
            FROM manual_review mr
            JOIN ingredients i ON i.id = mr.ingredient_id
            WHERE mr.status='PENDING'
            ORDER BY i.canonical_name, mr.score DESC
            """
        )
        rows = cursor.fetchall()

    args.output.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    print(f"exported {len(rows)} rows -> {args.output}")
    print("Fill decision with APPROVED or REJECTED, then run 08_apply_manual_review.py")


if __name__ == "__main__":
    main()
