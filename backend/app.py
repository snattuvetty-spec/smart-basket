from flask import Flask, jsonify, redirect, session
from flask_cors import CORS
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")
CORS(app)

# ── Register blueprints ───────────────────────────────────────────────────────
from routes.prices import prices_bp
from routes.auth import auth_bp

app.register_blueprint(prices_bp)
app.register_blueprint(auth_bp)

# ── Health check ──────────────────────────────────────────────────────────────
@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200

# ── Root redirect ─────────────────────────────────────────────────────────────
@app.route("/")
def index():
    if 'username' in session:
        return redirect('/app')
    return redirect('/login')

# ── Main app redirect (after login) ──────────────────────────────────────────
@app.route("/app")
def main_app():
    if 'username' not in session:
        return redirect('/login')
    return redirect("https://smart-basket-63ww.onrender.com")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(debug=False, host="0.0.0.0", port=port)
