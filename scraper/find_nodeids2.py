"""
Test Woolworths department specials URLs to find their categoryIds.
"""
import requests
import time

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

DEPARTMENTS = [
    ("Online Only Specials",   "/shop/browse/specials/online-only-specials",        "online-only-specials"),
    ("Bundles",                "/shop/browse/specials/bundles",                     "bundles"),
    ("Everyday Market",        "/shop/browse/specials/everyday-market-specials-and-offers", "everyday-market-specials-and-offers"),
    ("Freezer",                "/shop/browse/freezer/freezer-specials",             "freezer-specials"),
    ("Fruit & Veg",            "/shop/browse/fruit-veg/fruit-veg-specials",         "fruit-veg-specials"),
    ("Poultry Meat Seafood",   "/shop/browse/poultry-meat-seafood/poultry-meat-seafood-specials", "poultry-meat-seafood-specials"),
    ("Dairy Eggs Fridge",      "/shop/browse/dairy-eggs-fridge/dairy-eggs-fridge-specials", "dairy-eggs-fridge-specials"),
    ("Snacks Confectionery",   "/shop/browse/snacks-confectionery/snacks-confectionery-specials", "snacks-confectionery-specials"),
    ("Drinks",                 "/shop/browse/drinks/drinks-specials",               "drinks-specials"),
    ("Pantry",                 "/shop/browse/pantry/pantry-specials",               "pantry-specials"),
    ("Bakery",                 "/shop/browse/bakery/bakery-specials",               "bakery-specials"),
]

session = requests.Session()
session.get(
    "https://www.woolworths.com.au/shop/browse/specials",
    headers={"User-Agent": UA, "Accept": "text/html"},
    timeout=20
)
time.sleep(1)

print(f"{'Label':<30} {'Count':>8}  CategoryId")
print("-" * 70)

for label, url, slug in DEPARTMENTS:
    try:
        payload = {
            "categoryId": slug,
            "pageNumber": 1,
            "pageSize": 1,
            "sortType": "TraderRelevance",
            "url": url,
            "location": url,
            "formatObject": f'{{"name":"{label}"}}',
            "isSpecial": True,
            "isBundle": False,
            "isMobile": False,
            "filters": [],
        }
        r = session.post(
            "https://www.woolworths.com.au/apis/ui/browse/category",
            json=payload,
            headers={
                "User-Agent": UA,
                "Accept": "application/json, text/plain, */*",
                "Content-Type": "application/json",
                "Origin": "https://www.woolworths.com.au",
                "Referer": f"https://www.woolworths.com.au{url}",
                "x-requested-with": "OnlineShopping.WebApp",
            },
            timeout=15
        )
        if r.status_code == 200:
            data = r.json()
            count = data.get("TotalRecordCount", 0)
            # Try to get actual categoryId from response
            cat_id = data.get("CategoryId", slug)
            if count > 0:
                print(f"{label:<30} {count:>8}  *** {cat_id} ***")
            else:
                print(f"{label:<30} {count:>8}  {cat_id}")
        else:
            print(f"{label:<30} HTTP {r.status_code}")
        time.sleep(0.8)
    except Exception as e:
        print(f"{label:<30} ERROR: {e}")
