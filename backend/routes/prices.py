from flask import Blueprint, jsonify, request

prices_bp = Blueprint("prices", __name__)

MOCK_PRICES = {
    "Full Cream Milk 2L":       {"woolworths": 3.50, "coles": 3.30, "aldi": 2.99},
    "White Bread":              {"woolworths": 3.00, "coles": 2.80, "aldi": 1.99},
    "Free Range Eggs 12pk":     {"woolworths": 6.50, "coles": 6.20, "aldi": 5.49},
    "Chicken Breast 1kg":       {"woolworths": 11.00, "coles": 10.50, "aldi": 8.99},
    "Pasta 500g":               {"woolworths": 2.50, "coles": 2.20, "aldi": 1.49},
    "Canned Tomatoes 400g":     {"woolworths": 1.80, "coles": 1.60, "aldi": 1.19},
    "Olive Oil 750ml":          {"woolworths": 9.00, "coles": 8.50, "aldi": 6.99},
    "Baby Spinach 120g":        {"woolworths": 3.50, "coles": 3.30, "aldi": 2.79},
    "Toilet Paper 12pk":        {"woolworths": 10.00, "coles": 9.50, "aldi": 7.99},
    "Bananas 1kg":              {"woolworths": 3.50, "coles": 3.20, "aldi": 2.89},
}

@prices_bp.route("/api/prices", methods=["POST"])
def get_prices():
    items = request.json.get("items", [])
    result = {item: MOCK_PRICES.get(item) for item in items}
    return jsonify(result)

@prices_bp.route("/api/search", methods=["GET"])
def search():
    q = request.args.get("q", "").lower()
    matches = [k for k in MOCK_PRICES if q in k.lower()]
    return jsonify(matches)