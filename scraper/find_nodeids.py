"""
Quick script to discover which Woolworths NodeIds have products.
Run this to find the NodeId for the 40% off / general specials category.
"""
import requests
import time

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

# NodeIds to test - trying a range around known working ones
CANDIDATES = [
    "specialsgroup.3072",
    "specialsgroup.3075",
    "specialsgroup.3076",
    "specialsgroup.3600",
    "specialsgroup.3650",
    "specialsgroup.3660",
    "specialsgroup.3665",
    "specialsgroup.3667",
    "specialsgroup.3669",
    "specialsgroup.3670",
    "specialsgroup.3671",
    "specialsgroup.3672",
    "specialsgroup.3674",
    "specialsgroup.3675",
    "specialsgroup.3677",
    "specialsgroup.3678",
    "specialsgroup.3679",
    "specialsgroup.3680",
    "specialsgroup.3690",
    "specialsgroup.3695",
    "specialsgroup.3700",
    "specialsgroup.3710",
    "specialsgroup.3715",
    "specialsgroup.3720",
    "specialsgroup.3725",
    "specialsgroup.3730",
]

session = requests.Session()

# Warm up
session.get(
    "https://www.woolworths.com.au/shop/browse/specials",
    headers={"User-Agent": UA, "Accept": "text/html"},
    timeout=20
)
time.sleep(1)

print(f"{'NodeId':<30} {'Count':>8}  Label")
print("-" * 60)

for node_id in CANDIDATES:
    try:
        payload = {
            "categoryId": node_id,
            "pageNumber": 1,
            "pageSize": 1,
            "sortType": "TraderRelevance",
            "url": "/shop/browse/specials",
            "location": "/shop/browse/specials",
            "formatObject": '{"name":"Specials"}',
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
                "Referer": "https://www.woolworths.com.au/shop/browse/specials",
                "x-requested-with": "OnlineShopping.WebApp",
            },
            timeout=15
        )
        if r.status_code == 200:
            data = r.json()
            count = data.get("TotalRecordCount", 0)
            # Get category name from first product if available
            bundles = data.get("Bundles") or []
            if count > 0:
                print(f"{node_id:<30} {count:>8}  *** HAS PRODUCTS ***")
            else:
                print(f"{node_id:<30} {count:>8}")
        else:
            print(f"{node_id:<30} HTTP {r.status_code}")
        time.sleep(0.8)
    except Exception as e:
        print(f"{node_id:<30} ERROR: {e}")
