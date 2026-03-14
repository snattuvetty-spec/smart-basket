from flask import Flask, jsonify, redirect, session
from flask_cors import CORS
from dotenv import load_dotenv
import os
import threading

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")
CORS(app, supports_credentials=True, origins=[
    "https://smart-basket-63ww.onrender.com",
    "http://localhost:5173",
    "http://localhost:3000",
])

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

# ── Start Telegram bot in background thread ───────────────────────────────────
def start_telegram_bot():
    try:
        from telegram_bot import run
        run()
    except Exception as e:
        print(f"Telegram bot error: {e}")

if os.environ.get("TELEGRAM_BOT_TOKEN"):
    bot_thread = threading.Thread(target=start_telegram_bot, daemon=True)
    bot_thread.start()
    print("Telegram bot started in background.")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(debug=False, host="0.0.0.0", port=port)
