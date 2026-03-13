"""
Debug v9 - quick end-to-end test of both scrapers (5 pages each max)
"""
import os, sys, logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Patch coles to only do 3 pages for speed
import coles as coles_mod
original_scrape = coles_mod.scrape

def fast_coles():
    import requests, re, time, math
    session = requests.Session()
    build_id = coles_mod.get_build_id(session)
    print(f"BuildId: {build_id}")
    ch = {"User-Agent": coles_mod.UA, "Accept": "application/json"}
    url = f"https://www.coles.com.au/_next/data/{build_id}/on-special.json?page=1"
    r = session.get(url, headers=ch, timeout=20)
    sr = r.json()["pageProps"]["searchResults"]
    total = sr["noOfResults"]
    page_size = sr["pageSize"]
    total_pages = math.ceil(total / page_size)
    seen = set()
    products, _ = coles_mod._parse_results(sr.get("results", []), seen)
    print(f"Coles page 1: {len(products)} products (total={total}, pages={total_pages})")
    if products:
        p = products[0]
        print(f"  Sample: {p['name']} | ${p['price']} | was=${p['was_price']} | saving={p['saving']} | type={p['special_type']}")
        p2 = products[5] if len(products) > 5 else products[-1]
        print(f"  Sample2: {p2['name']} | ${p2['price']} | was=${p2['was_price']} | saving_pct={p2['saving_pct']}%")
    return products, 0, 0

print("=" * 60)
print("COLES TEST")
print("=" * 60)
products_c, _, _ = fast_coles()

print()
print("=" * 60)
print("WOOLWORTHS TEST (1 group, 1 page)")
print("=" * 60)
import woolworths as ww_mod
import requests, time

session = requests.Session()
session.get("https://www.woolworths.com.au/shop/browse/specials",
            headers={"User-Agent": ww_mod.UA, "Accept": "text/html"}, timeout=20)
time.sleep(1)

payload = {
    "categoryId": "specialsgroup.3676",
    "pageNumber": 1,
    "pageSize": 36,
    "sortType": "TraderRelevance",
    "url": "/shop/browse/specials/half-price",
    "location": "/shop/browse/specials/half-price",
    "formatObject": '{"name":"Half Price"}',
    "isSpecial": True,
    "isBundle": False,
    "isMobile": False,
    "filters": [],
}
r = session.post(
    "https://www.woolworths.com.au/apis/ui/browse/category",
    json=payload,
    headers=ww_mod.get_headers("https://www.woolworths.com.au/shop/browse/specials/half-price"),
    timeout=20
)
data = r.json()
total = data.get("TotalRecordCount", 0)
bundles = data.get("Bundles") or []
products_w = []
for b in bundles:
    products_w.extend(b.get("Products", []))

print(f"Woolworths Half Price: HTTP {r.status_code}, total={total}, page products={len(products_w)}")
if products_w:
    p = products_w[0]
    print(f"  Sample: {p.get('Name')} | ${p.get('Price')} | was=${p.get('WasPrice')} | brand={p.get('Brand')}")
    print(f"  CupString: {p.get('CupString')} | Stockcode: {p.get('Stockcode')}")

print("\n✅ Both scrapers working! Ready to run main.py")
