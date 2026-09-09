from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


STEPS = [
    "01_profile_raw_json.py",
    "02_clean_recipes.py",
    "03a_build_unit_weight_map.py",
    "03_normalize_recipes.py",
    "04_import_recipes_mysql.py",
    "04a_import_reference_maps.py",
    "05_import_nutrition_excel.py",
    "06_match_ingredient_nutrition.py",
    "07_export_manual_review.py",
]


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    python_dir = script_dir.parent
    project_root = python_dir.parent

    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        f"{python_dir}{os.pathsep}{existing}" if existing else str(python_dir)
    )

    print(f"Project root : {project_root}")
    print(f"Python dir   : {python_dir}")
    print(f"Python exe   : {sys.executable}")
    print(f"PYTHONPATH   : {env['PYTHONPATH']}")

    for step in STEPS:
        script = script_dir / step
        print(f"\n===== RUN {step} =====", flush=True)
        subprocess.run(
            [sys.executable, str(script)],
            check=True,
            cwd=str(python_dir),
            env=env,
        )
        print(f"===== DONE {step} =====", flush=True)

    print("\nPipeline stopped after exporting manual review.")
    print("Edit data/manual_review/manual_review.json, then run:")
    print("  uv run python scripts/08_apply_manual_review.py")
    print("  uv run python scripts/09_calculate_recipe_nutrition.py")


if __name__ == "__main__":
    main()
