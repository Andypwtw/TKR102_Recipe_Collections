from __future__ import annotations

import os
import sys
from pathlib import Path

PYTHON_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = PYTHON_DIR.parent
if str(PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(PYTHON_DIR))

from app.services.normalization import normalize_text


def main() -> None:
    checks = {
        "python_executable": sys.executable,
        "python_dir": str(PYTHON_DIR),
        "project_root": str(PROJECT_ROOT),
        "virtual_env": os.environ.get("VIRTUAL_ENV"),
        "uv_project_environment": os.environ.get("UV_PROJECT_ENVIRONMENT"),
        "pythonpath": os.environ.get("PYTHONPATH"),
        "raw_json_exists": (PROJECT_ROOT / "data/raw/ytower_seq_recipes.json").exists(),
        "normalization_import": normalize_text("  牛肉  ") == "牛肉",
    }
    for key, value in checks.items():
        print(f"{key}: {value}")

    if not checks["raw_json_exists"]:
        raise SystemExit("ERROR: data/raw/ytower_seq_recipes.json not found")
    if not checks["normalization_import"]:
        raise SystemExit("ERROR: app import/normalization check failed")


if __name__ == "__main__":
    main()
