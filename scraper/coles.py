"""
Coles Specials Scraper
Fetches this week's specials from Coles and returns structured data.
"""

import requests
import time
import random
import logging

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
]

# Coles on-special API endpoint
COLES_SPECIALS_URL = "https://www.coles.com.au/api/2.0/collections/on-special"
COLES_BROWSE_URL  = "https://www.coles.com.au/on-special"


def get_headers():
    """Return realistic browser headers for Coles."""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-AU,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://www.coles.com.au/on-special",
        "Origin": "https://www.coles.com.au",
        "sec-ch-ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
        "sec-ch-ua-mobile": "?0",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
    }


def scrape_page(session, page=1):
    """Scrape one page of Coles specials."""
    params = {
        "page": page,
        "pageSize": 48,
        "sortBy": "priceDesc",
    }

    try:
        time.sleep(random.uniform(1.5, 3.0))
        resp = session.get(
            COLES_SPECIALS_URL,
            params=params,
            headers=get_headers(),
            timeout=15
        )

        if resp.status_code == 403:
            raise BlockedError(f"Coles returned 403 on page {page}")
        if resp.status_code == 429:
            raise BlockedError(f"Coles rate limited (429) on page {page}")
        if resp.status_code != 200:
            logger.warning(f"Coles returned {resp.status_code} on page {page}")
            return [], 0

        data = resp.json()
        results = data.get("results", [])
        total_pages = data.get("pageCount", 1)

        specials = []
        for item in results:
            pricing = item.get("pricing", {})
            special_price = pricing.get("now")
            was_price = pricing.get("was")

            if not special_price:
                continue

            saving = None
            saving_pct = None
            if was_price and was_price > special_price:
                saving = round(was_price - special_price, 2)
                saving_pct = round((saving / was_price) * 100)

            # Extract category from the item's brand/categories if available
            category = ""
            categories = item.get("categories", [])
            if categories:
                category = categories[-1].get("name", "")

            specials.append({
                "store": "coles",
                "stockcode": str(item.get("id", "")),
                "name": item.get("name", ""),
                "brand": item.get("brand", ""),
                "description": item.get("description", ""),
                "category": category,
                "price": special_price,
                "was_price": was_price,
                "saving": saving,
                "saving_pct": saving_pct,
                "unit_price": pricing.get("unitOfMeasurePrice", ""),
                "thumbnail": item.get("imageUris", [None])[0],
                "is_half_price": saving_pct and saving_pct >= 45,
                "special_type": pricing.get("offerDescription", ""),
            })

        return specials, total_pages

    except BlockedError:
        raise
    except Exception as e:
        logger.error(f"Error scraping Coles page {page}: {e}")
        return [], 0


def scrape_all_specials():
    """
    Scrape all Coles specials.
    Returns list of specials and a status dict.
    """
    session = requests.Session()
    all_specials = []
    seen_ids = set()
    errors = []

    # Warm up session
    try:
        session.get(COLES_BROWSE_URL, headers=get_headers(), timeout=15)
        time.sleep(2)
    except Exception as e:
        logger.warning(f"Could not warm up Coles session: {e}")

    try:
        # Get first page to find total pages
        specials, total_pages = scrape_page(session, page=1)
        for item in specials:
            if item["stockcode"] not in seen_ids:
                seen_ids.add(item["stockcode"])
                all_specials.append(item)

        logger.info(f"Coles page 1: {len(specials)} specials, {total_pages} total pages")

        # Scrape remaining pages (cap at 20 pages = ~960 items)
        for page in range(2, min(total_pages + 1, 21)):
            try:
                specials, _ = scrape_page(session, page=page)
                for item in specials:
                    if item["stockcode"] not in seen_ids:
                        seen_ids.add(item["stockcode"])
                        all_specials.append(item)
                logger.info(f"Coles page {page}: {len(specials)} specials")
            except BlockedError as e:
                errors.append(str(e))
                break
            except Exception as e:
                errors.append(f"Page {page}: {str(e)}")
                continue

    except BlockedError as e:
        errors.append(str(e))
        logger.error(str(e))

    status = {
        "store": "coles",
        "total": len(all_specials),
        "errors": errors,
        "blocked": any("403" in e or "429" in e or "Blocked" in e for e in errors),
    }

    return all_specials, status


class BlockedError(Exception):
    pass
