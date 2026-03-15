from flask import Flask, jsonify, redirect, session, request
from flask_cors import CORS
from dotenv import load_dotenv
import os
import threading
import subprocess
import sys
from datetime import datetime, timezone

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

# ── Scrape state ──────────────────────────────────────────────────────────────
SCRAPE_SECRET = os.environ.get("SCRAPE_SECRET", "")
_scrape_status = {
    "running": False,
    "last_triggered": None,
    "last_finished": None,
    "last_exit_code": None,
    "last_output": None,
}

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

# ── Internal: trigger scraper ─────────────────────────────────────────────────
@app.route("/internal/scrape", methods=["POST"])
def trigger_scrape():
    if not SCRAPE_SECRET or request.headers.get("X-Scrape-Key") != SCRAPE_SECRET:
        return jsonify({"error": "unauthorized"}), 401

    if _scrape_status["running"]:
        return jsonify({"status": "already running", "triggered": _scrape_status["last_triggered"]}), 409

    def run_scraper():
        _scrape_status["running"] = True
        _scrape_status["last_triggered"] = datetime.now(timezone.utc).isoformat()
        _scrape_status["last_output"] = None
        _scrape_status["last_exit_code"] = None

        try:
            scraper_path = os.path.join(os.path.dirname(__file__), "..", "scraper", "main.py")
            result = subprocess.run(
                [sys.executable, scraper_path],
                env={**os.environ},
                capture_output=True,
                text=True,
                timeout=600  # 10 min max
            )
            _scrape_status["last_exit_code"] = result.returncode
            # Keep last 5000 chars of output to avoid memory bloat
            combined = (result.stdout or "") + (result.stderr or "")
            _scrape_status["last_output"] = combined[-5000:] if combined else "(no output)"
            print(f"Scraper finished with exit code {result.returncode}")
            print(combined[-2000:])
        except subprocess.TimeoutExpired:
            _scrape_status["last_exit_code"] = -1
            _scrape_status["last_output"] = "Scraper timed out after 10 minutes"
            print("Scraper timed out")
        except Exception as e:
            _scrape_status["last_exit_code"] = -1
            _scrape_status["last_output"] = str(e)
            print(f"Scraper error: {e}")
        finally:
            _scrape_status["running"] = False
            _scrape_status["last_finished"] = datetime.now(timezone.utc).isoformat()

    thread = threading.Thread(target=run_scraper, daemon=True)
    thread.start()
    return jsonify({"status": "scraper started", "triggered": _scrape_status["last_triggered"]}), 202


# ── Internal: scrape status ───────────────────────────────────────────────────
@app.route("/internal/scrape-status", methods=["GET"])
def scrape_status():
    if not SCRAPE_SECRET or request.headers.get("X-Scrape-Key") != SCRAPE_SECRET:
        return jsonify({"error": "unauthorized"}), 401

    return jsonify({
        "running":          _scrape_status["running"],
        "last_triggered":   _scrape_status["last_triggered"],
        "last_finished":    _scrape_status["last_finished"],
        "last_exit_code":   _scrape_status["last_exit_code"],
        "last_output":      _scrape_status["last_output"],
    }), 200


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
