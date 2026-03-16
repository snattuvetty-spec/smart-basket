"""
Woolworths specials scraper - uses browse/category API with real NodeIds
"""
import requests
import time
import logging
import random

logger = logging.getLogger(__name__)

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

# Special type groups to scrape — NodeId: (label, url_slug)
SPECIAL_GROUPS = {
    "specialsgroup.3676":  ("Half Price",           "half-price"),
    "specialsgroup.3694":  ("Lower Shelf Price",    "lower-shelf-price"),
    "specialsgroup.3673":  ("Everyday Low Price",   "everyday-low-price"),
    "specialsgroup.3719":  ("Autumn Price",         "autumn-price"),
    "specialsgroup.3668":  ("Buy More Save More",   "buy-more-save-more"),
    "specialsgroup.3072":  ("Specials",             "specials"),
    "specialsgroup.3675":  ("Save Now",             "save-now"),


}

PAGE_SIZE = 36


def get_headers(referer):
    return {
        "User-Agent": UA,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-AU,en;q=0.9",
        "Content-Type": "application/json",
        "Origin": "https://www.woolworths.com.au",
        "Referer": referer,
        "x-requested-with": "OnlineShopping.WebApp",
    }


def scrape():
    session = requests.Session()

    # Warm up — get cookies
    try:
        session.get(
            "https://www.woolworths.com.au/shop/browse/specials",
            headers={"User-Agent": UA, "Accept": "text/html"},
            timeout=20
        )
        time.sleep(1)
    except Exception as e:
        logger.warning(f"Woolworths warmup failed: {e}")

    all_products = []
    seen_stockcodes = set()
    total_blocked = 0
    total_errors = 0

    for node_id, (label, url_slug) in SPECIAL_GROUPS.items():
        group_count = 0
        page = 1

        while True:
            try:
                referer = f"https://www.woolworths.com.au/shop/browse/specials/{url_slug}"
                payload = {
                    "categoryId": node_id,
                    "pageNumber": page,
                    "pageSize": PAGE_SIZE,
                    "sortType": "TraderRelevance",
                    "url": f"/shop/browse/specials/{url_slug}",
                    "location": f"/shop/browse/specials/{url_slug}",
                    "formatObject": f'{{"name":"{label}"}}',
                    "isSpecial": True,
                    "isBundle": False,
                    "isMobile": False,
                    "filters": [],
                }

                r = session.post(
                    "https://www.woolworths.com.au/apis/ui/browse/category",
                    json=payload,
                    headers=get_headers(referer),
                    timeout=20
                )

                if r.status_code == 403:
                    logger.warning(f"Woolworths blocked (403) on {label} page {page}")
                    total_blocked += 1
                    break

                if r.status_code != 200:
                    logger.warning(f"Woolworths {label} page {page}: HTTP {r.status_code}")
                    total_errors += 1
                    break

                data = r.json()
                total_count = data.get("TotalRecordCount", 0)
                bundles = data.get("Bundles") or []

                page_products = []
                for bundle in bundles:
                    for p in bundle.get("Products", []):
                        stockcode = str(p.get("Stockcode", ""))
                        if not stockcode or stockcode in seen_stockcodes:
                            continue
                        seen_stockcodes.add(stockcode)

                        price = p.get("Price")
                        was_price = p.get("WasPrice")
                        saving = None
                        saving_pct = None
                        if price and was_price and was_price > price:
                            saving = round(was_price - price, 2)
                            saving_pct = round((saving / was_price) * 100, 1)
                        if price is None:   # ← ADD THIS
                           continue        # ← AND THIS

                        page_products.append({
                            "store": "woolworths",
                            "stockcode": stockcode,
                            "name": p.get("Name", ""),
                            "brand": p.get("Brand", ""),
                            "category": label,
                            "price": price,
                            "was_price": was_price,
                            "saving": saving,
                            "saving_pct": saving_pct,
                            "unit_price": p.get("CupString", ""),
                            "thumbnail": p.get("SmallImageFile", ""),
                            "is_half_price": node_id == "specialsgroup.3676",
                            "special_type": label,
                        })

                group_count += len(page_products)
                all_products.extend(page_products)

                logger.info(f"Woolworths '{label}' page {page}: {len(page_products)} products (total so far: {group_count}/{total_count})")

                # Check if more pages
                fetched_so_far = page * PAGE_SIZE
                if fetched_so_far >= total_count or len(page_products) == 0:
                    break

                page += 1
                time.sleep(random.uniform(0.8, 1.5))

            except requests.exceptions.Timeout:
                logger.warning(f"Woolworths timeout on {label} page {page}")
                total_errors += 1
                break
            except Exception as e:
                logger.error(f"Woolworths error on {label} page {page}: {e}")
                total_errors += 1
                break

        logger.info(f"Woolworths '{label}': {group_count} specials scraped")
        time.sleep(random.uniform(1.0, 2.0))

    logger.info(f"Woolworths total: {len(all_products)} unique specials, {total_blocked} blocked, {total_errors} errors")
    return all_products, total_blocked, total_errors
