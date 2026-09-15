from __future__ import annotations
import json, re
from pathlib import Path
from app.services.normalization import clean_text, parse_number, normalize_unit, direct_weight_g

SRC = Path("/workspace/data/processed/recipes_clean.json")
OUT = Path("/workspace/data/processed/recipes_normalized.json")

LINE_SPLIT = re.compile(r"\s*\|\s*")
AMOUNT_RE = re.compile(r"^(?P<name>.*?)(?P<qty>\d+(?:\.\d+)?|\d+\s*/\s*\d+)\s*(?P<unit>公斤|公克|克|kg|g|毫升|ml|公升|L|l|大匙|小匙|斤|顆|朵|片|格|隻|尾|條|根|杯|碗|匙)?")

def parse_materials(text):
    result=[]
    for idx, raw in enumerate(LINE_SPLIT.split(clean_text(text)), 1):
        raw=raw.strip()
        if not raw:
            continue
        m=AMOUNT_RE.match(raw)
        if m:
            name=clean_text(m.group("name"))
            qty=parse_number(m.group("qty"))
            unit=normalize_unit(m.group("unit") or "")
        else:
            name=raw; qty=None; unit=""
        result.append({
            "line_no": idx,
            "raw_text": raw,
            "raw_name": name,
            "canonical_name": name,
            "quantity_value": qty,
            "unit": unit,
            "weight_g": direct_weight_g(qty, unit),
        })
    return result

def main():
    rows=json.loads(SRC.read_text(encoding="utf-8"))
    out=[]
    for r in rows:
        out.append({
            "seq": r.get("SEQ"),
            "name": r.get("食譜名稱"),
            "published_date": r.get("上線日期"),
            "raw_keywords": r.get("關鍵字"),
            "source_url": r.get("食譜網址"),
            "steps": r.get("做法步驟"),
            "ingredients": parse_materials(r.get("材料","")),
        })
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"normalized={len(out)}")

if __name__ == "__main__":
    main()
