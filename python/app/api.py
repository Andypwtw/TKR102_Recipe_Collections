from __future__ import annotations

from functools import wraps

from flask import Flask, jsonify, request

from app.config import settings
from app.db import get_connection
from app.services.recommendation import recommend_by_ingredients

app = Flask(__name__)


def require_hermes_key(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        expected = settings.hermes_api_key
        if expected and request.headers.get("X-API-Key") != expected:
            return jsonify({"error": "unauthorized"}), 401
        return fn(*args, **kwargs)
    return wrapper


@app.get("/health")
def health():
    try:
        with get_connection() as conn, conn.cursor() as cursor:
            cursor.execute("SELECT 1 AS ok")
            row = cursor.fetchone()
        return jsonify({"status": "ok", "mysql": bool(row and row["ok"] == 1)})
    except Exception as exc:
        return jsonify({"status": "error", "mysql": False, "detail": str(exc)}), 503


@app.get("/api/v1/recipes/<seq>")
def recipe_detail(seq: str):
    with get_connection() as conn, conn.cursor() as cursor:
        cursor.execute(
            "SELECT id, seq, name, published_date, source_url, raw_keywords, steps FROM recipes WHERE seq=%s",
            (seq,),
        )
        recipe = cursor.fetchone()
        if not recipe:
            return jsonify({"error": "recipe_not_found"}), 404
        cursor.execute(
            """
            SELECT ri.line_no, ri.raw_text, i.canonical_name, ri.raw_amount_text,
                   ri.quantity_value, u.canonical_unit, ri.weight_g,
                   ri.is_estimated, ri.needs_manual_review
            FROM recipe_ingredients ri
            JOIN ingredients i ON i.id = ri.ingredient_id
            LEFT JOIN units u ON u.id = ri.unit_id
            WHERE ri.recipe_id=%s
            ORDER BY ri.line_no
            """,
            (recipe["id"],),
        )
        recipe["ingredients"] = cursor.fetchall()
        cursor.execute(
            "SELECT * FROM recipe_nutrition_summary WHERE recipe_id=%s",
            (recipe["id"],),
        )
        recipe["nutrition"] = cursor.fetchone()
    return jsonify(recipe)


@app.get("/api/v1/recipes/search")
def recipe_search():
    q = (request.args.get("q") or "").strip()
    limit = min(max(int(request.args.get("limit", "20")), 1), 100)
    if not q:
        return jsonify({"items": []})
    pattern = f"%{q}%"
    with get_connection() as conn, conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT DISTINCT r.seq, r.name, r.source_url
            FROM recipes r
            LEFT JOIN recipe_ingredients ri ON ri.recipe_id = r.id
            LEFT JOIN ingredients i ON i.id = ri.ingredient_id
            WHERE r.name LIKE %s OR i.canonical_name LIKE %s
            ORDER BY r.seq
            LIMIT %s
            """,
            (pattern, pattern, limit),
        )
        rows = cursor.fetchall()
    return jsonify({"items": rows})


@app.post("/api/v1/recommend")
def recommend():
    payload = request.get_json(silent=True) or {}
    ingredients = payload.get("ingredients") or []
    if not isinstance(ingredients, list) or not all(isinstance(x, str) for x in ingredients):
        return jsonify({"error": "ingredients_must_be_string_array"}), 400
    limit = int(payload.get("limit", 5))
    return jsonify({"items": recommend_by_ingredients(ingredients, limit=limit)})


@app.post("/api/v1/hermes/recommend")
@require_hermes_key
def hermes_recommend():
    payload = request.get_json(silent=True) or {}
    ingredients = payload.get("ingredients") or []
    if not isinstance(ingredients, list) or not all(isinstance(x, str) for x in ingredients):
        return jsonify({"error": "ingredients_must_be_string_array"}), 400
    limit = int(payload.get("limit", 5))
    return jsonify(
        {
            "tool": "recipe_recommendation",
            "input": {"ingredients": ingredients, "limit": limit},
            "results": recommend_by_ingredients(ingredients, limit=limit),
        }
    )


@app.get("/openapi.json")
def openapi_spec():
    spec = {
        "openapi": "3.0.3",
        "info": {"title": "Recipe Collections API", "version": "0.2.0"},
        "paths": {
            "/api/v1/hermes/recommend": {
                "post": {
                    "summary": "Recommend recipes by available ingredients",
                    "security": [{"ApiKeyAuth": []}],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["ingredients"],
                                    "properties": {
                                        "ingredients": {"type": "array", "items": {"type": "string"}},
                                        "limit": {"type": "integer", "default": 5, "minimum": 1, "maximum": 50},
                                    },
                                }
                            }
                        },
                    },
                    "responses": {"200": {"description": "Recommendation results"}},
                }
            }
        },
        "components": {
            "securitySchemes": {
                "ApiKeyAuth": {"type": "apiKey", "in": "header", "name": "X-API-Key"}
            }
        },
    }
    return jsonify(spec)
