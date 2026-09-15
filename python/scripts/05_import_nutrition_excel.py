from __future__ import annotations
import json
from pathlib import Path
import pandas as pd
from app.db import get_connection

XLSX=Path("/workspace/data/reference/food_nutrition_2025.xlsx")

def pick(row,*names):
    for n in names:
        if n in row and pd.notna(row[n]):
            return row[n]
    return None

def main():
    if not XLSX.exists():
        print(f"skip: {XLSX} not found")
        return
    df=pd.read_excel(XLSX)
    with get_connection() as conn, conn.cursor() as cur:
        for _, r in df.iterrows():
            d=r.to_dict()
            name=pick(d,"食品名稱","樣品名稱","Food Name")
            if not name:
                continue
            cur.execute(
                """
                INSERT INTO nutrition_source(food_code,food_name,energy_kcal,protein_g,fat_g,carbohydrate_g,sodium_mg,raw_data)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    str(pick(d,"整合編號","食品樣品代碼","食品代碼") or ""),
                    str(name),
                    pick(d,"熱量(kcal)","熱量","修正熱量"),
                    pick(d,"粗蛋白(g)","蛋白質","蛋白質(g)"),
                    pick(d,"粗脂肪(g)","脂肪","脂肪(g)"),
                    pick(d,"總碳水化合物(g)","碳水化合物","碳水化合物(g)"),
                    pick(d,"鈉(mg)","鈉"),
                    json.dumps(d, ensure_ascii=False, default=str),
                )
            )
        conn.commit()
    print(f"nutrition rows imported={len(df)}")

if __name__ == "__main__":
    main()
