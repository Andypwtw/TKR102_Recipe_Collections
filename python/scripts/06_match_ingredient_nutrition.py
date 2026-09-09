from __future__ import annotations

from pathlib import Path
import argparse
import re
from difflib import SequenceMatcher

import sys

PYTHON_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = PYTHON_DIR.parent
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))

from app.db import get_connection
from app.services.normalization import normalize_text


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Match normalized ingredients to nutrition source rows.")
    parser.add_argument("--auto-threshold", type=float, default=0.90)
    parser.add_argument("--review-threshold", type=float, default=0.72)
    parser.add_argument("--top-k", type=int, default=3)
    return parser.parse_args()


def match_key(value: str) -> str:
    text = normalize_text(value)
    text = re.sub(r"\([^)]*\)", "", text)
    text = re.sub(r"[\s,，、/\\-]+", "", text)
    for word in ("新鮮", "冷凍", "熟", "生", "切片", "切絲", "切塊", "末", "絲", "段"):
        text = text.replace(word, "")
    return text


def similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    if a in b or b in a:
        return 0.96 * min(len(a), len(b)) / max(len(a), len(b)) + 0.04
    return SequenceMatcher(None, a, b).ratio()


def main() -> None:
    args = parse_args()
    with get_connection() as conn, conn.cursor() as cursor:
        cursor.execute("SELECT id, canonical_name FROM ingredients ORDER BY id")
        ingredients = cursor.fetchall()
        cursor.execute("SELECT id, sample_name, common_name FROM nutrition_source ORDER BY id")
        nutrition_rows = cursor.fetchall()

        candidates = []
        for row in nutrition_rows:
            names = [row["sample_name"]]
            if row.get("common_name"):
                names.extend(re.split(r"[,，、;；]", str(row["common_name"])))
            keys = {match_key(name) for name in names if name}
            candidates.append((row["id"], row["sample_name"], keys))

        auto_count = 0
        review_count = 0
        for ingredient in ingredients:
            key = match_key(ingredient["canonical_name"])
            ranked = []
            for nutrition_id, sample_name, keys in candidates:
                score = max((similarity(key, candidate_key) for candidate_key in keys), default=0.0)
                ranked.append((score, nutrition_id, sample_name))
            ranked.sort(reverse=True)
            best_score, best_id, best_name = ranked[0] if ranked else (0, None, None)

            if best_id is not None and best_score >= args.auto_threshold:
                cursor.execute(
                    """
                    INSERT INTO ingredient_nutrition_map
                        (ingredient_id, nutrition_source_id, match_method, match_score, status)
                    VALUES (%s, %s, 'name_similarity', %s, 'AUTO')
                    ON DUPLICATE KEY UPDATE
                        nutrition_source_id=VALUES(nutrition_source_id),
                        match_method=VALUES(match_method),
                        match_score=VALUES(match_score),
                        status='AUTO'
                    """,
                    (ingredient["id"], best_id, best_score),
                )
                cursor.execute("DELETE FROM manual_review WHERE ingredient_id=%s AND status='PENDING'", (ingredient["id"],))
                auto_count += 1
            else:
                cursor.execute("DELETE FROM manual_review WHERE ingredient_id=%s AND status='PENDING'", (ingredient["id"],))
                for score, nutrition_id, sample_name in ranked[: args.top_k]:
                    if score < args.review_threshold:
                        continue
                    cursor.execute(
                        """
                        INSERT INTO manual_review
                            (ingredient_id, candidate_nutrition_id, candidate_name, score, status)
                        VALUES (%s, %s, %s, %s, 'PENDING')
                        """,
                        (ingredient["id"], nutrition_id, sample_name, score),
                    )
                    review_count += 1

        print(f"auto matched ingredients: {auto_count}")
        print(f"manual review candidate rows: {review_count}")


if __name__ == "__main__":
    main()
