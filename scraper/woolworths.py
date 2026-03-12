"""
Woolworths Specials Scraper
Fetches this week's specials from Woolworths and returns structured data.
"""

import requests
import time
import random
import logging

logger = logging.getLogger(__name__)

# Rotate user agents to avoid fingerprinting
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3.1 Safari/605.1.15",
]

WOOLWORTHS_SEARCH_URL = "https://www.woolworths.com.au/apis/ui/Search/products"

# Categories to scrape specials from
CATEGORIES = [
    "fruit",
    "vegetables",
    "meat",
    "chicken",
    "seafood",
    "dairy",
    "bread",
    "snacks",
    "drinks",
    "frozen",
    "breakfast",
    "pasta",
    "cleaning",
    "health",
    "baby",
]


def get_headers():
    """Return realistic browser headers."""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-AU,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Content-Type": "application/json",
        "Origin": "https://www.woolworths.com.au",
        "Referer": "https://www.woolworths.com.au/shop/browse/specials",
        "x-requested-with": "OnlineShopping.WebApp",
        "sec-ch-ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
    }


def scrape_category(session, category, page=1):
    """Scrape one page of specials for a given category."""
    payload = {
        "Filters": [{"Key": "specials", "Items": [{"Term": "halfprice"}]}],
        "IsSpecial": True,
        "Location": f"/shop/browse/specials",
        "PageNumber": page,
        "PageSize": 36,
        "SearchTerm": category,
        "SortType": "TraderRelevance",
    }

    try:
        time.sleep(random.uniform(1.5, 3.5))  # Polite delay
        resp = session.post(
            WOOLWORTHS_SEARCH_URL,
            json=payload,
            headers=get_headers(),
            timeout=15
        )

        if resp.status_code == 403:
            raise BlockedError(f"Woolworths returned 403 for category '{category}'")
        if resp.status_code == 429:
            raise BlockedError(f"Woolworths rate limited (429) for category '{category}'")
        if resp.status_code != 200:
            logger.warning(f"Woolworths returned {resp.status_code} for '{category}'")
            return [], 0

        data = resp.json()
        products = data.get("Products", [])
        total_pages = data.get("TotalRecordCount", 0) // 36 + 1

        specials = []
        for p in products:
            info = p.get("Product", p)  # handle nested or flat
            if not info.get("IsOnSpecial"):
                continue

            special_price = info.get("Price")
            was_price = info.get("WasPrice")
            if not special_price:
                continue

            saving = None
            saving_pct = None
            if was_price and was_price > special_price:
                saving = round(was_price - special_price, 2)
                saving_pct = round((saving / was_price) * 100)

            specials.append({
                "store": "woolworths",
                "stockcode": str(info.get("Stockcode", "")),
                "name": info.get("Name", ""),
                "brand": info.get("Brand", ""),
                "description": info.get("Description", ""),
                "category": category,
                "price": special_price,
                "was_price": was_price,
                "saving": saving,
                "saving_pct": saving_pct,
                "unit_price": info.get("CupString", ""),
                "thumbnail": info.get("SmallImageFile", ""),
                "is_half_price": saving_pct and saving_pct >= 45,
                "special_type": info.get("SpecialType", ""),
            })

        return specials, total_pages

    except BlockedError:
        raise
    except Exception as e:
        logger.error(f"Error scraping Woolworths category '{category}': {e}")
        return [], 0


def scrape_all_specials():
    """
    Scrape all Woolworths specials across categories.
    Returns list of specials and a status dict.
    """
    session = requests.Session()
    all_specials = []
    seen_stockcodes = set()
    errors = []

    # First warm up the session by hitting the homepage
    try:
        session.get(
            "https://www.woolworths.com.au/shop/browse/specials",
            headers=get_headers(),
            timeout=15
        )
        time.sleep(2)
    except Exception as e:
        logger.warning(f"Could not warm up Woolworths session: {e}")

    for category in CATEGORIES:
        try:
            specials, total_pages = scrape_category(session, category, page=1)

            # Scrape up to 3 pages per category
            for page in range(2, min(total_pages + 1, 4)):
                more, _ = scrape_category(session, category, page=page)
                specials.extend(more)

            # Deduplicate by stockcode
            for item in specials:
                if item["stockcode"] not in seen_stockcodes:
                    seen_stockcodes.add(item["stockcode"])
                    all_specials.append(item)

            logger.info(f"Woolworths '{category}': {len(specials)} specials")

        except BlockedError as e:
            errors.append(str(e))
            logger.error(str(e))
            break  # Stop scraping if blocked

        except Exception as e:
            errors.append(f"Category '{category}': {str(e)}")
            logger.error(f"Woolworths scrape error: {e}")
            continue

    status = {
        "store": "woolworths",
        "total": len(all_specials),
        "errors": errors,
        "blocked": any("403" in e or "429" in e or "Blocked" in e for e in errors),
    }

    return all_specials, status


class BlockedError(Exception):
    pass
