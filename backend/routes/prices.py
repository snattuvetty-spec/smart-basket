import os
import requests
from flask import Blueprint, jsonify, request

prices_bp = Blueprint("prices", __name__)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://bqwexelzzxgolvzmmovo.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJxd2V4ZWx6enhnb2x2em1tb3ZvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzMxNjkwNDEsImV4cCI6MjA4ODc0NTA0MX0.GZFS5ifuNOD6f3xpHMhIB0F7XURlve-cdV3T9BXIOj4")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
}


def search_supabase(name):
    """Search specials table for a product name, return cheapest price per store."""
    # Use ilike for fuzzy match — try progressively shorter queries if no results
    words = name.strip().split()
    for num_words in range(len(words), 0, -1):
        query = " ".join(words[:num_words])
        url = (
            f"{SUPABASE_URL}/rest/v1/specials"
            f"?select=store,price,name"
            f"&name=ilike.*{requests.utils.quote(query)}*"
            f"&order=price.asc"
            f"&limit=50"
        )
        resp = requests.get(url, headers=HEADERS, timeout=8)
        if resp.status_code == 200:
            rows = resp.json()
            if rows:
                # Get cheapest price per store
                prices = {}
                for row in rows:
                    store = row["store"]
                    price = row["price"]
                    if price and (store not in prices or price < prices[store]):
                        prices[store] = price
                if prices:
                    return prices
    return None


def search_suggestions(query):
    """Return product name suggestions from specials table."""
    url = (
        f"{SUPABASE_URL}/rest/v1/specials"
        f"?select=name"
        f"&name=ilike.*{requests.utils.quote(query)}*"
        f"&order=name.asc"
        f"&limit=20"
    )
    resp = requests.get(url, headers=HEADERS, timeout=8)
    if resp.status_code == 200:
        rows = resp.json()
        # Deduplicate names
        seen = set()
        names = []
        for row in rows:
            n = row["name"]
            if n not in seen:
                seen.add(n)
                names.append(n)
        return names[:8]
    return []


@prices_bp.route("/api/prices", methods=["POST"])
def get_prices():
    items = request.json.get("items", [])
    result = {}
    for item in items:
        prices = search_supabase(item)
        result[item] = prices  # None if not found
    return jsonify(result)


@prices_bp.route("/api/search", methods=["GET"])
def search():
    q = request.args.get("q", "").strip()
    if not q or len(q) < 2:
        return jsonify([])
    suggestions = search_suggestions(q)
    return jsonify(suggestions)
