"""
SmartPicks Telegram Bot
Runs as a background process on Render.
When users message /start, it replies with their chat ID.
"""
import os
import time
import logging
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

WELCOME_MSG = """👋 Welcome to SmartPicks Alerts!

Your Telegram Chat ID is:
<code>{chat_id}</code>

Copy this ID and paste it into SmartPicks to enable notifications.

You'll get alerted whenever items on your shopping list go on special at Woolworths or Coles! 🛒"""

def get_updates(offset=None):
    try:
        params = {"timeout": 30, "allowed_updates": ["message"]}
        if offset:
            params["offset"] = offset
        resp = requests.get(f"{BASE_URL}/getUpdates", params=params, timeout=35)
        if resp.status_code == 200:
            return resp.json().get("result", [])
    except Exception as e:
        logger.error(f"getUpdates error: {e}")
    return []

def send_message(chat_id, text):
    try:
        requests.post(f"{BASE_URL}/sendMessage", json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }, timeout=10)
    except Exception as e:
        logger.error(f"sendMessage error: {e}")

def run():
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set!")
        return

    logger.info("SmartPicks Telegram bot started (@smartpicksAlerts_bot)")
    offset = None

    while True:
        updates = get_updates(offset)
        for update in updates:
            offset = update["update_id"] + 1
            message = update.get("message", {})
            if not message:
                continue
            chat_id = message["chat"]["id"]
            text = message.get("text", "").strip()
            first_name = message["from"].get("first_name", "there")

            logger.info(f"Message from {first_name} ({chat_id}): {text}")

            if text.startswith("/start"):
                send_message(chat_id, WELCOME_MSG.format(chat_id=chat_id))
            elif text.startswith("/help"):
                send_message(chat_id, f"Your Chat ID is: <code>{chat_id}</code>\n\nPaste this into SmartPicks settings to enable alerts.")
            else:
                send_message(chat_id, f"Your Chat ID is: <code>{chat_id}</code>\n\nUse /start to see setup instructions.")

        if not updates:
            time.sleep(1)

if __name__ == "__main__":
    run()
