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

from app.services.normalization import normalize_text


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Clean YTower raw recipe JSON and split material lines.")
    parser.add_argument("--input", type=Path, default=PROJECT_ROOT / "data" / "raw" / "ytower_seq_recipes.json")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "data" / "processed" / "recipes_clean.json")
    return parser.parse_args()


def normalize_date(value: str) -> str | None:
    text = normalize_text(value)
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            pass
    return None


def main() -> None:
    args = parse_args()
    with args.input.open("r", encoding="utf-8") as f:
        rows = json.load(f)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    skipped = 0
    seen_seq: set[str] = set()
    cleaned_rows = []

    for row in rows:
        seq = normalize_text(row.get("SEQ"))
        name = normalize_text(row.get("食譜名稱"))
        if not seq or not name:
            skipped += 1
            continue
        if seq in seen_seq:
            skipped += 1
            continue
        seen_seq.add(seq)

        raw_keywords = normalize_text(row.get("關鍵字"))
        keywords = [x.strip() for x in raw_keywords.split(",") if x.strip()]
        materials = normalize_text(row.get("材料"))
        material_lines = [x.strip() for x in materials.split("|") if x.strip()]

        cleaned_rows.append({
            "seq": seq,
            "name": name,
            "published_date": normalize_date(row.get("上線日期", "")),
            "keywords": keywords,
            "raw_keywords": raw_keywords,
            "source_url": normalize_text(row.get("食譜網址")),
            "steps": normalize_text(row.get("做法步驟")),
            "materials": [
                {"line_no": i, "raw_text": material}
                for i, material in enumerate(material_lines, start=1)
            ],
        })
        written += 1

    args.output.write_text(
        json.dumps(cleaned_rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"cleaned recipes: {written}")
    print(f"skipped rows: {skipped}")
    print(f"output: {args.output}")


if __name__ == "__main__":
    main()
