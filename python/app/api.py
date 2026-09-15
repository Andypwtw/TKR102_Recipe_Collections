from __future__ import annotations
from flask import Flask, jsonify, request
from app.db import get_connection
from app.mongo_db import get_mongo_client
from app.services.recommendation import recommend_by_ingredients

app = Flask(__name__)

@app.get("/health")
def health():
    status = {"api": "ok", "mysql": "unknown", "mongodb": "unknown"}
    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT 1 AS ok")
            cur.fetchone()
        status["mysql"] = "ok"
    except Exception as e:
        status["mysql"] = f"error: {e}"
    try:
        get_mongo_client().admin.command("ping")
        status["mongodb"] = "ok"
    except Exception as e:
        status["mongodb"] = f"error: {e}"
    code = 200 if status["mysql"] == "ok" and status["mongodb"] == "ok" else 503
    return jsonify(status), code

@app.get("/api/v1/recipes/search")
def search_recipes():
    q = (request.args.get("q") or "").strip()
    limit = min(max(int(request.args.get("limit", "20")), 1), 100)
    if not q:
        return jsonify({"items": []})
    p = f"%{q}%"
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT DISTINCT r.seq, r.name, r.source_url
            FROM recipes r
            LEFT JOIN recipe_ingredients ri ON ri.recipe_id = r.id
            LEFT JOIN ingredients i ON i.id = ri.ingredient_id
            WHERE r.name LIKE %s OR i.canonical_name LIKE %s
            ORDER BY r.seq
            LIMIT %s
            """,
            (p, p, limit),
        )
        rows = cur.fetchall()
    return jsonify({"items": rows})

@app.get("/api/v1/recipes/<seq>")
def get_recipe(seq: str):
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM recipes WHERE seq=%s", (seq,))
        recipe = cur.fetchone()
        if not recipe:
            return jsonify({"error": "not found"}), 404
        cur.execute(
            """
            SELECT i.canonical_name, ri.quantity_value, u.canonical_unit, ri.weight_g
            FROM recipe_ingredients ri
            LEFT JOIN ingredients i ON i.id=ri.ingredient_id
            LEFT JOIN units u ON u.id=ri.unit_id
            WHERE ri.recipe_id=%s
            ORDER BY ri.line_no
            """,
            (recipe["id"],),
        )
        recipe["ingredients"] = cur.fetchall()
    return jsonify(recipe)

@app.post("/api/v1/recommend")
@app.post("/api/v1/hermes/recommend")
def recommend():
    payload = request.get_json(silent=True) or {}
    ingredients = payload.get("ingredients", [])
    limit = int(payload.get("limit", 10))
    return jsonify({"items": recommend_by_ingredients(ingredients, limit)})
