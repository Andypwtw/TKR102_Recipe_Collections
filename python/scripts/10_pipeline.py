from __future__ import annotations
import os, subprocess
from pathlib import Path

def main():
    script_dir=Path(__file__).resolve().parent
    python_dir=script_dir.parent
    steps=[
        "01_profile_mongodb.py",
        "02_clean_recipes.py",
        "03a_build_unit_weight_map.py",
        "03_normalize_recipes.py",
        "04_import_recipes_mysql.py",
        "04a_import_reference_maps.py",
        "05_import_nutrition_excel.py",
        "06_match_ingredient_nutrition.py",
        "07_export_manual_review.py",
    ]
    env=os.environ.copy()
    env["PYTHONPATH"]=str(python_dir)
    env["UV_PROJECT_ENVIRONMENT"]="/opt/venv"
    for step in steps:
        print(f"===== RUN {step} =====", flush=True)
        subprocess.run(["uv","run","python",str(script_dir/step)],check=True,cwd=str(python_dir),env=env)
        print(f"===== DONE {step} =====", flush=True)
    print("\nPipeline stopped after exporting manual review.")
    print("Edit data/manual_review/manual_review.json, then run:")
    print("  uv run python scripts/08_apply_manual_review.py")
    print("  uv run python scripts/09_calculate_recipe_nutrition.py")

if __name__ == "__main__":
    main()
