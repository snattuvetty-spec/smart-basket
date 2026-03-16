import requests
import json
import time

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

session = requests.Session()

# Warmup
warm = session.get(
    "https://www.woolworths.com.au/shop/browse/specials/half-price",
    headers={"User-Agent": UA, "Accept": "text/html"},
    timeout=25
)
print(f"Warmup: {warm.status_code}, cookies: {dict(session.cookies)}")
time.sleep(2)

# Test POST
payload = {
    "categoryId": "specialsgroup.3676",
    "pageNumber": 1,
    "pageSize": 48,
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
    headers={
        "User-Agent": UA,
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Origin": "https://www.woolworths.com.au",
        "Referer": "https://www.woolworths.com.au/shop/browse/specials/half-price",
        "x-requested-with": "OnlineShopping.WebApp",
    },
    timeout=20
)

print(f"Status: {r.status_code}")
print(f"Response: {r.text[:2000]}")