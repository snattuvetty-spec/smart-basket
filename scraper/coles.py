"""
Coles specials scraper - uses Next.js _next/data route
Build ID is fetched fresh each run so it never goes stale.
"""
import requests
import re
import time
import logging
import random
import math

logger = logging.getLogger(__name__)

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
IMAGE_BASE = "https://cdn.productimages.coles.com.au/productimages"

# Fallback: if we can't scrape buildId, use a known recent one
# Update this manually if the scraper breaks after a Coles deploy
FALLBACK_BUILD_ID = "20260310.4-d51173fab603623c68e557a054992d8939a1a9e7"


def get_build_id(session):
    """Fetch the current Next.js buildId from the on-special page."""
    headers = {
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-AU,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    r = session.get("https://www.coles.com.au/on-special", headers=headers, timeout=20)
    
    # Try multiple patterns
    patterns = [
        r'"buildId"\s*:\s*"([^"]+)"',
        r'/_next/static/([^/]+)/_buildManifest',
        r'"runtimeConfig".*?"buildId"\s*:\s*"([^"]+)"',
    ]
    for pattern in patterns:
        match = re.search(pattern, r.text)
        if match:
            return match.group(1)
    
    # Log first 500 chars to help debug
    logger.warning(f"Could not find buildId. Page status: {r.status_code}, start: {r.text[:200]}")
    logger.warning(f"Using fallback buildId: {FALLBACK_BUILD_ID}")
    return FALLBACK_BUILD_ID


def scrape():
    session = requests.Session()
    total_blocked = 0
    total_errors = 0

    # Step 1: get fresh buildId
    try:
        build_id = get_build_id(session)
        logger.info(f"Coles buildId: {build_id}")
        time.sleep(1)
    except Exception as e:
        logger.error(f"Failed to get Coles buildId: {e}")
        build_id = FALLBACK_BUILD_ID
        logger.info(f"Using fallback buildId: {build_id}")

    ch = {
        "User-Agent": UA,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-AU,en;q=0.9",
        "Referer": "https://www.coles.com.au/on-special",
    }
    all_products = []
    seen_ids = set()

    # Step 2: get page 1 to find total
    try:
        url = f"https://www.coles.com.au/_next/data/{build_id}/on-special.json?page=1"
        r = session.get(url, headers=ch, timeout=20)
        if r.status_code != 200:
            logger.error(f"Coles page 1 returned HTTP {r.status_code}")
            return [], 0, 1

        sr = r.json()["pageProps"]["searchResults"]
        total = sr["noOfResults"]
        page_size = sr["pageSize"]
        total_pages = math.ceil(total / page_size)
        logger.info(f"Coles: {total} specials across {total_pages} pages (pageSize={page_size})")

        products, dupes = _parse_results(sr.get("results", []), seen_ids)
        all_products.extend(products)
        logger.info(f"Coles page 1: {len(products)} products")

    except Exception as e:
        logger.error(f"Coles page 1 error: {e}")
        return [], 0, 1

    # Step 3: pages 2..N
    for page in range(2, total_pages + 1):
        try:
            url = f"https://www.coles.com.au/_next/data/{build_id}/on-special.json?page={page}"
            r = session.get(url, headers=ch, timeout=20)

            if r.status_code == 403:
                logger.warning(f"Coles blocked (403) on page {page}")
                total_blocked += 1
                break

            if r.status_code != 200:
                logger.warning(f"Coles page {page}: HTTP {r.status_code}")
                total_errors += 1
                break

            sr = r.json()["pageProps"]["searchResults"]
            results = sr.get("results", [])
            if not results:
                logger.info(f"Coles page {page}: no results, stopping")
                break

            products, dupes = _parse_results(results, seen_ids)
            all_products.extend(products)
            logger.info(f"Coles page {page}/{total_pages}: {len(products)} products (total: {len(all_products)})")

            time.sleep(random.uniform(0.5, 1.2))

        except Exception as e:
            logger.error(f"Coles page {page} error: {e}")
            total_errors += 1
            break

    logger.info(f"Coles total: {len(all_products)} unique specials, {total_blocked} blocked, {total_errors} errors")
    return all_products, total_blocked, total_errors


def _parse_results(results, seen_ids):
    products = []
    dupes = 0

    for p in results:
        if p.get("_type") != "PRODUCT":
            continue

        product_id = str(p.get("id", ""))
        if not product_id or product_id in seen_ids:
            dupes += 1
            continue
        seen_ids.add(product_id)

        pricing = p.get("pricing") or {}
        price = pricing.get("now")
        was_price = pricing.get("was") or None
        if was_price == 0:
            was_price = None

        save_amount = pricing.get("saveAmount")
        special_type = pricing.get("specialType") or pricing.get("promotionType") or "SPECIAL"
        offer_desc = pricing.get("offerDescription", "")
        comparable = pricing.get("comparable", "")

        saving_pct = None
        if price and was_price and was_price > price:
            saving_pct = round(((was_price - price) / was_price) * 100, 1)

        image_uris = p.get("imageUris", [])
        thumbnail = ""
        if image_uris:
            uri = image_uris[0].get("uri", "")
            thumbnail = IMAGE_BASE + uri if uri.startswith("/") else uri

        category = ""
        heirs = p.get("onlineHeirs", [])
        if heirs:
            h = heirs[0]
            category = h.get("subCategory") or h.get("category") or ""

        is_half_price = "half" in special_type.lower() or (
            was_price and price and round(price / was_price, 2) <= 0.51
        )

        products.append({
            "store": "coles",
            "stockcode": product_id,
            "name": p.get("name", ""),
            "brand": p.get("brand", ""),
            "category": category,
            "price": price,
            "was_price": was_price,
            "saving": save_amount,
            "saving_pct": saving_pct,
            "unit_price": comparable,
            "thumbnail": thumbnail,
            "is_half_price": is_half_price,
            "special_type": special_type,
            "offer_description": offer_desc,
        })

    return products, dupes
