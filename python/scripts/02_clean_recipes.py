from __future__ import annotations
import json
from pathlib import Path
from app.mongo_db import load_raw_recipes
from app.services.normalization import clean_text

OUT = Path("/workspace/data/processed/recipes_clean.json")

def main():
    rows = load_raw_recipes()
    cleaned = []
    for r in rows:
        item = dict(r)
        for key in ["SEQ","食譜名稱","上線日期","關鍵字","食譜網址","材料","做法步驟"]:
            if key in item and isinstance(item[key], str):
                item[key] = clean_text(item[key])
        cleaned.append(item)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(cleaned, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"cleaned={len(cleaned)} -> {OUT}")

if __name__ == "__main__":
    main()
