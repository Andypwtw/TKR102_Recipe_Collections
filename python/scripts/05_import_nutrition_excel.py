from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

import sys

PYTHON_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = PYTHON_DIR.parent
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))

from app.db import get_connection


COLUMN_MAP = {
    "廢棄率(%)": "waste_rate_pct",
    "熱量(kcal)": "energy_kcal",
    "修正熱量(kcal)": "corrected_energy_kcal",
    "水分(g)": "water_g",
    "粗蛋白(g)": "protein_g",
    "粗脂肪(g)": "fat_g",
    "飽和脂肪(g)": "saturated_fat_g",
    "總碳水化合物(g)": "carbohydrate_g",
    "膳食纖維(g)": "dietary_fiber_g",
    "鈉(mg)": "sodium_mg",
    "鉀(mg)": "potassium_mg",
    "鈣(mg)": "calcium_mg",
    "鎂(mg)": "magnesium_mg",
    "鐵(mg)": "iron_mg",
    "鋅(mg)": "zinc_mg",
    "磷(mg)": "phosphorus_mg",
    "視網醇當量(RE)(ug)": "vitamin_a_re_ug",
    "維生素B1(mg)": "vitamin_b1_mg",
    "維生素B2(mg)": "vitamin_b2_mg",
    "菸鹼素(mg)": "niacin_mg",
    "維生素B6(mg)": "vitamin_b6_mg",
    "維生素B12(ug)": "vitamin_b12_ug",
    "葉酸(ug)": "folate_ug",
    "維生素C(mg)": "vitamin_c_mg",
    "維生素E總量(mg)": "vitamin_e_mg",
    "膽固醇(mg)": "cholesterol_mg",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import the 2025 Taiwan food nutrition Excel into MySQL.")
    parser.add_argument("--input", type=Path, default=PROJECT_ROOT / "data" / "reference" / "food_nutrition_2025.xlsx")
    parser.add_argument("--sheet", default="台灣食品成分表")
    return parser.parse_args()


def clean_value(value: Any) -> Any:
    # The source workbook uses 116 in many cells as a non-numeric/sentinel-like value.
    if value in (None, "", "116"):
        return None
    return value


def to_number(value: Any) -> float | None:
    value = clean_value(value)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def main() -> None:
    args = parse_args()
    workbook = load_workbook(args.input, read_only=True, data_only=True)
    ws = workbook[args.sheet]

    rows = ws.iter_rows(values_only=True)
    note_row = next(rows)  # row 1: "每100 g可食部分"
    headers = [str(x).strip() if x is not None else "" for x in next(rows)]
    header_index = {name: i for i, name in enumerate(headers) if name}

    insert_columns = [
        "source_code", "food_category", "sample_name", "content_description", "common_name",
        *COLUMN_MAP.values(), "raw_data", "source_version",
    ]
    placeholders = ", ".join(["%s"] * len(insert_columns))
    updates = ", ".join(f"{col}=VALUES({col})" for col in insert_columns if col != "source_code")
    sql = f"""
        INSERT INTO nutrition_source ({', '.join(insert_columns)})
        VALUES ({placeholders})
        ON DUPLICATE KEY UPDATE {updates}
    """

    count = 0
    with get_connection() as conn, conn.cursor() as cursor:
        for row in rows:
            source_code = clean_value(row[header_index["整合編號"]])
            sample_name = clean_value(row[header_index["樣品名稱"]])
            if not source_code or not sample_name:
                continue

            raw_dict = {
                header: clean_value(row[idx])
                for header, idx in header_index.items()
            }
            # JSON must not contain non-serializable Excel objects.
            raw_json = json.dumps(raw_dict, ensure_ascii=False, default=str)

            values = [
                str(source_code),
                clean_value(row[header_index["食品分類"]]),
                str(sample_name),
                clean_value(row[header_index["內容物描述"]]),
                clean_value(row[header_index["俗名"]]),
            ]
            values.extend(to_number(row[header_index[src]]) for src in COLUMN_MAP)
            values.extend([raw_json, "2025"])
            cursor.execute(sql, values)
            count += 1
            if count % 500 == 0:
                conn.commit()
                print(f"imported {count} nutrition rows")

    print(f"done: {count} nutrition rows")
    print(f"source note: {note_row[0] if note_row else ''}")


if __name__ == "__main__":
    main()
