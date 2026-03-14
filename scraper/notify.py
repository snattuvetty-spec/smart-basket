"""
SmartPicks Telegram Notification System
Runs after scraper completes — checks all users' saved list items
against current specials and sends Telegram alerts for matches.
"""
import os
import requests
import logging
from supabase import create_client

logger = logging.getLogger(__name__)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def send_telegram(chat_id, message):
    if not TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not set — skipping.")
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        resp = requests.post(url, json={
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }, timeout=10)
        logger.info(f"Telegram response: {resp.status_code} {resp.text[:100]}")
        return resp.status_code == 200
    except Exception as e:
        logger.error(f"Telegram error for chat_id {chat_id}: {e}")
        return False


def check_and_notify():
    if not TELEGRAM_BOT_TOKEN:
        logger.warning("No TELEGRAM_BOT_TOKEN — skipping notifications.")
        return 0

    # Get all users with telegram connected
    try:
        users = supabase.table('users').select('username, name, telegram_chat_id').not_.is_('telegram_chat_id', 'null').execute().data
        logger.info(f"Users with Telegram: {len(users)}")
    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        return 0

    if not users:
        logger.info("No users with Telegram connected.")
        return 0

    total_sent = 0

    for user in users:
        username = user['username']
        chat_id = user['telegram_chat_id']
        user_name = user.get('name', username)

        # Get user's saved list items (column is 'name')
        try:
            rows = supabase.table('list_items').select('name').eq('username', username).execute().data
            logger.info(f"User {username} has {len(rows)} list items")
        except Exception as e:
            logger.error(f"Error fetching list for {username}: {e}")
            continue

        if not rows:
            continue

        # Check each item against current specials
        matches = []
        for row in rows:
            product_name = row['name']
            words = product_name.strip().split()
            query = ' '.join(words[:3]) if len(words) >= 3 else product_name
            try:
                results = supabase.table('specials').select(
                    'name, store, price, was_price, saving_pct, is_half_price'
                ).ilike('name', f'%{query}%').order('saving_pct', desc=True).limit(3).execute().data
                logger.info(f"  '{product_name}' -> {len(results)} specials matches")
            except Exception as e:
                logger.error(f"Error searching specials for '{product_name}': {e}")
                continue

            if results:
                best = results[0]
                matches.append({
                    'list_name':    product_name,
                    'special_name': best['name'],
                    'store':        best['store'].title(),
                    'price':        best['price'],
                    'was_price':    best.get('was_price'),
                    'saving_pct':   best.get('saving_pct'),
                    'is_half_price': best.get('is_half_price', False),
                })

        if not matches:
            logger.info(f"No matches for {username}")
            continue

        # Build message
        lines = [f"🛒 <b>SmartPicks Alert for {user_name}!</b>\n"]
        lines.append(f"<b>{len(matches)} item{'s' if len(matches) > 1 else ''} from your list {'are' if len(matches) > 1 else 'is'} on special:</b>\n")

        for m in matches:
            store_emoji = '🟢' if m['store'].lower() == 'woolworths' else '🔴'
            half_tag = ' 🏷️ HALF PRICE' if m['is_half_price'] else ''
            pct_tag = f" (-{round(m['saving_pct'])}%)" if m['saving_pct'] else ''
            price_line = f"${m['price']:.2f}"
            if m['was_price']:
                price_line += f" <s>${m['was_price']:.2f}</s>"
            lines.append(f"{store_emoji} <b>{m['special_name']}</b>{half_tag}")
            lines.append(f"   {price_line}{pct_tag}")
            lines.append("")

        lines.append(f"👉 <a href='https://smart-basket-63ww.onrender.com'>View all specials</a>")
        message = '\n'.join(lines)

        sent = send_telegram(chat_id, message)
        if sent:
            total_sent += 1
            logger.info(f"Notified {username} ({len(matches)} matches)")
        else:
            logger.warning(f"Failed to notify {username}")

    logger.info(f"Notifications sent: {total_sent}/{len(users)} users")
    return total_sent


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    check_and_notify()
