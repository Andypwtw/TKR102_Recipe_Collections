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
    parser = argparse.ArgumentParser(description="Import unit-weight and density reference maps into MySQL.")
    parser.add_argument("--unit-weights", type=Path, default=PROJECT_ROOT / "data" / "reference" / "unit_weight_map.json")
    parser.add_argument("--densities", type=Path, default=PROJECT_ROOT / "data" / "reference" / "ingredient_density_map.json")
    return parser.parse_args()


def get_ingredient_id(cursor, name: str) -> int | None:
    cursor.execute("SELECT id FROM ingredients WHERE canonical_name=%s", (name,))
    row = cursor.fetchone()
    return int(row["id"]) if row else None


def get_unit_id(cursor, unit: str) -> int | None:
    cursor.execute("SELECT id FROM units WHERE canonical_unit=%s", (unit,))
    row = cursor.fetchone()
    return int(row["id"]) if row else None


def import_unit_weights(cursor, path: Path) -> tuple[int, int]:
    imported = skipped = 0
    if not path.exists():
        return imported, skipped
    rows = json.loads(path.read_text(encoding="utf-8"))
    for row in rows:
            ingredient = (row.get("ingredient") or "").strip()
            unit = (row.get("unit") or "").strip()
            grams = row.get("grams_per_unit")
            if not ingredient or not unit or grams in (None, ""):
                skipped += 1
                continue
            ingredient_id = get_ingredient_id(cursor, ingredient)
            unit_id = get_unit_id(cursor, unit)
            if ingredient_id is None or unit_id is None:
                skipped += 1
                continue
            cursor.execute(
                """
                INSERT INTO ingredient_unit_weights
                    (ingredient_id, unit_id, grams_per_unit, source, note)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    grams_per_unit=VALUES(grams_per_unit),
                    source=VALUES(source),
                    note=VALUES(note)
                """,
                (
                    ingredient_id, unit_id, float(grams),
                    row.get("source"), row.get("note"),
                ),
            )
            imported += 1
    return imported, skipped


def import_densities(cursor, path: Path) -> tuple[int, int]:
    imported = skipped = 0
    if not path.exists():
        return imported, skipped
    rows = json.loads(path.read_text(encoding="utf-8"))
    for row in rows:
            ingredient = (row.get("ingredient") or "").strip()
            density = row.get("density_g_ml")
            status = (row.get("status") or "ACTIVE").strip().upper()
            if not ingredient or density in (None, ""):
                skipped += 1
                continue
            ingredient_id = get_ingredient_id(cursor, ingredient)
            if ingredient_id is None:
                skipped += 1
                continue
            cursor.execute(
                """
                INSERT INTO ingredient_densities
                    (ingredient_id, density_g_ml, density_type, confidence, status, source, note)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    density_g_ml=VALUES(density_g_ml),
                    density_type=VALUES(density_type),
                    confidence=VALUES(confidence),
                    status=VALUES(status),
                    source=VALUES(source),
                    note=VALUES(note)
                """,
                (
                    ingredient_id, float(density),
                    row.get("density_type") or "liquid",
                    row.get("confidence") or "中",
                    status,
                    row.get("source"), row.get("note"),
                ),
            )
            imported += 1
    return imported, skipped


def main() -> None:
    args = parse_args()
    with get_connection() as conn, conn.cursor() as cursor:
        unit_imported, unit_skipped = import_unit_weights(cursor, args.unit_weights)
        density_imported, density_skipped = import_densities(cursor, args.densities)
        conn.commit()
    print(f"ingredient_unit_weights imported={unit_imported}, skipped={unit_skipped}")
    print(f"ingredient_densities imported={density_imported}, skipped={density_skipped}")


if __name__ == "__main__":
    main()
