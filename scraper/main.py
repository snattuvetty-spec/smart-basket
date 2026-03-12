"""
SmartPicks Scraper - Main Runner
"""

import os
import sys
import logging
import smtplib
import json
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ── Logging first — before anything else ─────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

logger.info("SmartPicks Scraper starting...")
logger.info(f"Python version: {sys.version}")

# ── Config from env ───────────────────────────────────────────────────────────
SUPABASE_URL  = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY  = os.environ.get("SUPABASE_KEY", "")
ALERT_EMAIL   = os.environ.get("ALERT_EMAIL", "snattuvetty@hotmail.com")
MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
MAIL_FROM     = os.environ.get("MAIL_FROM", MAIL_USERNAME)

logger.info(f"SUPABASE_URL set: {bool(SUPABASE_URL)}")
logger.info(f"SUPABASE_KEY set: {bool(SUPABASE_KEY)}")
logger.info(f"MAIL_USERNAME set: {bool(MAIL_USERNAME)}")

if not SUPABASE_URL or not SUPABASE_KEY:
    logger.critical("SUPABASE_URL or SUPABASE_KEY is missing! Check GitHub secrets.")
    sys.exit(1)

from supabase import create_client
from woolworths import scrape_all_specials as scrape_woolworths
from coles import scrape_all_specials as scrape_coles


def send_alert(subject, body):
    if not MAIL_USERNAME or not MAIL_PASSWORD:
        logger.warning("No mail credentials — skipping alert email")
        return
    try:
        msg = MIMEMultipart()
        msg["From"]    = MAIL_FROM
        msg["To"]      = ALERT_EMAIL
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as server:
            server.login(MAIL_USERNAME, MAIL_PASSWORD)
            server.send_message(msg)
        logger.info(f"Alert email sent: {subject}")
    except Exception as e:
        logger.error(f"Could not send alert email: {e}")


def save_to_supabase(client, specials, scraped_at):
    if not specials:
        logger.warning("No specials to save.")
        return 0
    for item in specials:
        item["scraped_at"] = scraped_at
    chunk_size = 500
    saved = 0
    for i in range(0, len(specials), chunk_size):
        chunk = specials[i:i + chunk_size]
        client.table("specials").upsert(chunk, on_conflict="store,stockcode").execute()
        saved += len(chunk)
        logger.info(f"Saved chunk {i//chunk_size + 1}: {len(chunk)} records")
    return saved


def clear_old_specials(client, scraped_at):
    client.table("specials").delete().lt("scraped_at", scraped_at).execute()
    logger.info("Cleared old specials")


def log_scrape_run(client, woolies_status, coles_status, total_saved):
    try:
        client.table("scrape_log").insert({
            "scraped_at":          datetime.now(timezone.utc).isoformat(),
            "woolworths_total":    woolies_status["total"],
            "woolworths_blocked":  woolies_status["blocked"],
            "woolworths_errors":   json.dumps(woolies_status["errors"]),
            "coles_total":         coles_status["total"],
            "coles_blocked":       coles_status["blocked"],
            "coles_errors":        json.dumps(coles_status["errors"]),
            "total_saved":         total_saved,
        }).execute()
        logger.info("Scrape run logged to Supabase")
    except Exception as e:
        logger.warning(f"Could not log scrape run: {e}")


def main():
    logger.info("=" * 60)
    logger.info("SmartPicks Scraper - Main")
    logger.info("=" * 60)

    scraped_at = datetime.now(timezone.utc).isoformat()

    # ── Connect to Supabase ───────────────────────────────────────────────────
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("Connected to Supabase ✅")
    except Exception as e:
        logger.critical(f"Cannot connect to Supabase: {e}")
        send_alert("🚨 SmartPicks Scraper FAILED — Supabase error", str(e))
        sys.exit(1)

    all_specials = []
    alert_messages = []

    # ── Scrape Woolworths ─────────────────────────────────────────────────────
    logger.info("Scraping Woolworths...")
    try:
        woolies_specials, woolies_status = scrape_woolworths()
        all_specials.extend(woolies_specials)
        logger.info(f"Woolworths: {woolies_status['total']} specials")
        if woolies_status["blocked"]:
            alert_messages.append(f"🔴 WOOLWORTHS BLOCKED\n{woolies_status['errors']}")
        elif woolies_status["total"] == 0:
            alert_messages.append(f"⚠️ WOOLWORTHS — Zero specials. Errors: {woolies_status['errors']}")
    except Exception as e:
        woolies_status = {"total": 0, "blocked": False, "errors": [str(e)]}
        logger.error(f"Woolworths crashed: {e}")
        alert_messages.append(f"🔴 WOOLWORTHS CRASHED: {e}")

    # ── Scrape Coles ──────────────────────────────────────────────────────────
    logger.info("Scraping Coles...")
    try:
        coles_specials, coles_status = scrape_coles()
        all_specials.extend(coles_specials)
        logger.info(f"Coles: {coles_status['total']} specials")
        if coles_status["blocked"]:
            alert_messages.append(f"🔴 COLES BLOCKED\n{coles_status['errors']}")
        elif coles_status["total"] == 0:
            alert_messages.append(f"⚠️ COLES — Zero specials. Errors: {coles_status['errors']}")
    except Exception as e:
        coles_status = {"total": 0, "blocked": False, "errors": [str(e)]}
        logger.error(f"Coles crashed: {e}")
        alert_messages.append(f"🔴 COLES CRASHED: {e}")

    # ── Save to Supabase ──────────────────────────────────────────────────────
    total_saved = 0
    if all_specials:
        try:
            clear_old_specials(supabase, scraped_at)
            total_saved = save_to_supabase(supabase, all_specials, scraped_at)
            logger.info(f"Total saved: {total_saved}")
        except Exception as e:
            logger.error(f"Supabase save failed: {e}")
            alert_messages.append(f"🔴 SUPABASE SAVE FAILED: {e}")
    else:
        alert_messages.append("🔴 NO SPECIALS — both scrapers returned zero results.")

    # ── Log run ───────────────────────────────────────────────────────────────
    log_scrape_run(supabase, woolies_status, coles_status, total_saved)

    # ── Send alerts ───────────────────────────────────────────────────────────
    if alert_messages:
        send_alert(
            "🚨 SmartPicks Scraper Alert",
            f"Time: {scraped_at}\nWoolworths: {woolies_status['total']}\nColes: {coles_status['total']}\nSaved: {total_saved}\n\n"
            + "\n\n".join(alert_messages)
        )
    else:
        send_alert(
            f"✅ SmartPicks — {total_saved} specials loaded",
            f"Woolworths: {woolies_status['total']}\nColes: {coles_status['total']}\nTotal: {total_saved}\nTime: {scraped_at}"
        )

    if woolies_status["total"] == 0 and coles_status["total"] == 0:
        logger.error("Both scrapers returned zero — exiting with error")
        sys.exit(1)

    logger.info("Scraper complete ✅")


if __name__ == "__main__":
    main()
