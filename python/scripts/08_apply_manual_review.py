from __future__ import annotations
import json
from pathlib import Path
from app.db import get_connection

SRC=Path("/workspace/data/manual_review/manual_review.json")

def main():
    rows=json.loads(SRC.read_text(encoding="utf-8"))
    approved={}
    for r in rows:
        decision=(r.get("decision") or "").upper()
        if decision not in {"APPROVED","REJECTED"}:
            raise ValueError(f"review_id {r.get('review_id')} decision must be APPROVED/REJECTED")
        if decision=="APPROVED":
            iid=r["ingredient_id"]
            if iid in approved:
                raise ValueError(f"ingredient_id {iid} has more than one APPROVED")
            approved[iid]=r

    with get_connection() as conn, conn.cursor() as cur:
        for r in rows:
            decision=r["decision"].upper()
            cur.execute(
                "UPDATE manual_review SET status=%s,note=%s,reviewed_at=NOW() WHERE id=%s",
                (decision,r.get("note"),r["review_id"])
            )
            if decision=="APPROVED":
                cur.execute(
                    """
                    INSERT INTO ingredient_nutrition_map
                    (ingredient_id,nutrition_source_id,match_method,match_score,status,reviewed_at)
                    VALUES(%s,%s,'manual',%s,'APPROVED',NOW())
                    ON DUPLICATE KEY UPDATE
                    nutrition_source_id=VALUES(nutrition_source_id),
                    match_method='manual',
                    match_score=VALUES(match_score),
                    status='APPROVED',
                    reviewed_at=NOW()
                    """,
                    (r["ingredient_id"],r["candidate_nutrition_id"],float(r["score"]))
                )
        conn.commit()
    print(f"manual review applied. approved={len(approved)}, total={len(rows)}")

if __name__ == "__main__":
    main()
