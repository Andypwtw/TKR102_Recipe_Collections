from __future__ import annotations
from difflib import SequenceMatcher
from app.db import get_connection

AUTO_THRESHOLD=0.92
REVIEW_THRESHOLD=0.72
TOP_N=3

def sim(a,b):
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()

def main():
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT id,canonical_name FROM ingredients ORDER BY id")
        ingredients=cur.fetchall()
        cur.execute("SELECT id,food_name FROM nutrition_source")
        foods=cur.fetchall()

        cur.execute("DELETE FROM manual_review WHERE status='PENDING'")
        for idx, ing in enumerate(ingredients,1):
            name=ing["canonical_name"]
            exact=[f for f in foods if f["food_name"].strip()==name.strip()]
            if exact:
                f=exact[0]
                cur.execute(
                    """
                    INSERT INTO ingredient_nutrition_map(ingredient_id,nutrition_source_id,match_method,match_score,status)
                    VALUES(%s,%s,'exact',1.0,'APPROVED')
                    ON DUPLICATE KEY UPDATE nutrition_source_id=VALUES(nutrition_source_id),match_method='exact',match_score=1.0,status='APPROVED'
                    """,(ing["id"],f["id"])
                )
                continue

            scored=sorted(((sim(name,f["food_name"]),f) for f in foods), key=lambda x:x[0], reverse=True)[:TOP_N]
            if scored and scored[0][0] >= AUTO_THRESHOLD:
                s,f=scored[0]
                cur.execute(
                    """
                    INSERT INTO ingredient_nutrition_map(ingredient_id,nutrition_source_id,match_method,match_score,status)
                    VALUES(%s,%s,'fuzzy',%s,'APPROVED')
                    ON DUPLICATE KEY UPDATE nutrition_source_id=VALUES(nutrition_source_id),match_method='fuzzy',match_score=VALUES(match_score),status='APPROVED'
                    """,(ing["id"],f["id"],s)
                )
            else:
                for s,f in scored:
                    if s >= REVIEW_THRESHOLD:
                        cur.execute(
                            """
                            INSERT INTO manual_review(ingredient_id,candidate_nutrition_id,candidate_name,score,status)
                            VALUES(%s,%s,%s,%s,'PENDING')
                            """,(ing["id"],f["id"],f["food_name"],s)
                        )
            if idx % 100 == 0:
                conn.commit()
                print(f"matched {idx}/{len(ingredients)}")
        conn.commit()
    print("ingredient nutrition matching finished")

if __name__ == "__main__":
    main()
