"""Разведка russiabase: связка цен+координат, пагинация, бренды."""
import json
import re
import httpx

H = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
}


def get_next_data(url):
    with httpx.Client(timeout=30, trust_env=False, headers=H, follow_redirects=True) as c:
        r = c.get(url)
        m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', r.text, re.S)
        return json.loads(m.group(1))["props"]["pageProps"]


pp = get_next_data("https://russiabase.ru/prices?region=38")
listing = pp["listing"]["listing"]
mp = {m["poiid"]: m for m in pp["listingMap"]["listing"]}
pages = pp["listing"]["pages"]

print("Pages:", pages, "| listing/page:", len(listing), "| map total:", len(mp))
print("--- joined examples (price + coords) ---")
for st in listing[:5]:
    m = mp.get(st["poiid"], {})
    print(f"  {st['name']:28} | {st['address'][:35]:35} | "
          f"92={st['ai92']} 95={st['ai95']} dt={st['dt']} | "
          f"XY={m.get('X')},{m.get('Y')} | brand_id={st['brand_id']} | {st['LastUpdate']}")

# уникальные brand_id -> имя (из name)
print("--- brand_id -> name (из названий) ---")
brands = {}
for st in listing:
    bid = st["brand_id"]
    nm = st["name"].split("№")[0].strip()
    brands.setdefault(bid, set()).add(nm)
for bid, names in sorted(brands.items()):
    print(f"  {bid}: {list(names)[:3]}")

# проверим city-фильтр Иваново
print("--- city Иваново (city=154051) ---")
try:
    pp2 = get_next_data("https://russiabase.ru/prices?city=154051")
    print("  city listing:", len(pp2["listing"]["listing"]), "pages:", pp2["listing"]["pages"])
except Exception as e:
    print("  ERR:", e)
