from flask import Flask, jsonify
from flask_cors import CORS
from routes.prices import prices_bp

app = Flask(__name__)
CORS(app)
app.register_blueprint(prices_bp)

# ── Health check endpoint ──────────────────────────────────────────────────
# UptimeRobot pings this every 5 minutes to keep Render from sleeping
@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    app.run(debug=True, port=5000)
