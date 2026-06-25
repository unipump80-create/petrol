"""Жёсткие тесты кэша и логики выдачи /stations."""
import time

from app.services import cache as cache_mod
from app.models import Station, Price


# ---------- кэш ----------

def test_cache_set_get():
    cache_mod.cache_clear()
    cache_mod.cache_set("k", {"v": 1}, ttl_seconds=10)
    assert cache_mod.cache_get("k") == {"v": 1}


def test_cache_expires():
    cache_mod.cache_clear()
    cache_mod.cache_set("k", 1, ttl_seconds=0)  # мгновенно протух
    time.sleep(0.01)
    assert cache_mod.cache_get("k") is None


def test_cache_invalidate_and_clear():
    cache_mod.cache_clear()
    cache_mod.cache_set("a", 1, 100)
    cache_mod.cache_set("b", 2, 100)
    cache_mod.cache_invalidate("a")
    assert cache_mod.cache_get("a") is None
    assert cache_mod.cache_get("b") == 2
    cache_mod.cache_clear()
    assert cache_mod.cache_get("b") is None


def test_summary_cached_then_invalidated_by_clear(client, seeded):
    """/prices/summary кэшируется; cache_clear() сбрасывает."""
    cache_mod.cache_clear()
    r1 = client.get("/prices/summary").json()
    assert cache_mod.cache_get("summary") is not None  # закэшировалось
    cache_mod.cache_clear()
    assert cache_mod.cache_get("summary") is None
    r2 = client.get("/prices/summary").json()
    assert r1["stations"] == r2["stations"]


# ---------- выдача /stations ----------

def test_sort_price_puts_none_last(client, seeded):
    """Сортировка по цене: станции без цены — в конце."""
    data = client.get("/stations?fuel=ai95&sort=price").json()
    prices = [x["price"] for x in data]
    nums = [p for p in prices if p is not None]
    assert nums == sorted(nums)                 # числа по возрастанию
    # все None — после чисел
    first_none = next((i for i, p in enumerate(prices) if p is None), len(prices))
    assert all(p is None for p in prices[first_none:])


def test_brand_filter(client, seeded):
    data = client.get("/stations?brand=Лукойл").json()
    assert data and all(x["brand"] == "Лукойл" for x in data)


def test_available_from_fuel_types(client, seeded):
    """available = членство в fuel_types (не наличие цены)."""
    # s2 (ГПН) имеет fuel_types=[ai92], цены ai92 есть -> available по ai92
    data = client.get("/stations?fuel=ai95").json()
    gpn = next(x for x in data if x["brand"] == "Газпромнефть")
    assert gpn["available"] is False            # ai95 нет в fuel_types
    tn = next(x for x in data if x["brand"] == "Татнефть")
    assert tn["available"] is False             # fuel_types пуст


def test_station_detail_404(client, seeded):
    assert client.get("/stations/999999").status_code == 404


def test_station_detail_ok(client, seeded):
    sid = seeded.query(Station).filter_by(poiid="1").one().id
    r = client.get(f"/stations/{sid}")
    assert r.status_code == 200
    body = r.json()
    assert {p["fuel_type"] for p in body["prices"]} == {"ai92", "ai95"}
