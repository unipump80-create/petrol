"""Тесты HTTP-эндпоинтов."""
import app.routers.stations as stations_router


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_version(client):
    r = client.get("/version")
    assert r.status_code == 200
    assert "version" in r.json()


def test_summary_empty(client):
    """Пустая БД не должна падать."""
    r = client.get("/prices/summary")
    assert r.status_code == 200
    d = r.json()
    assert d["city"] == "Иваново"
    assert d["stations"] == 0
    assert d["fuels"] == []
    assert d["updated_at"] is None


def test_summary_populated(client, seeded):
    d = client.get("/prices/summary").json()
    assert d["stations"] == 3
    by = {f["fuel_type"]: f for f in d["fuels"]}
    assert by["ai92"]["count"] == 2
    assert by["ai92"]["min"] == 53.90
    assert by["ai92"]["max"] == 54.20
    assert by["ai95"]["count"] == 1
    # сортировка по коду топлива
    assert [f["fuel_type"] for f in d["fuels"]] == sorted(by)


def test_list_all(client, seeded):
    items = client.get("/stations").json()
    assert len(items) == 3


def test_list_filter_fuel_marks_unavailable(client, seeded):
    """fuel=ai95: продаёт только s1; остальные available=false, price=None."""
    items = client.get("/stations?fuel=ai95").json()
    by = {i["name"]: i for i in items}
    assert by["Лукойл №1"]["available"] is True
    assert by["Лукойл №1"]["price"] == 58.50
    assert by["ГПН №2"]["available"] is False
    assert by["ГПН №2"]["price"] is None
    assert by["ТН №3"]["available"] is False


def test_sort_price_unavailable_last(client, seeded):
    """Сортировка по цене не падает на None и кладёт недоступные в конец."""
    items = client.get("/stations?fuel=ai92&sort=price").json()
    prices = [i["price"] for i in items]
    assert prices[0] == 53.90  # дешевле
    assert prices[1] == 54.20
    assert prices[-1] is None  # ТН №3 без ai92


def test_sort_price_all_unavailable(client, seeded):
    """Крайний случай: топливо, которого нет ни у кого, — не должно падать."""
    r = client.get("/stations?fuel=ai100&sort=price")
    assert r.status_code == 200
    assert all(i["available"] is False for i in r.json())


def test_sort_name(client, seeded):
    items = client.get("/stations?sort=name").json()
    names = [i["name"] for i in items]
    assert names == sorted(names, key=str.lower)


def test_filter_brand(client, seeded):
    items = client.get("/stations?brand=Лукойл").json()
    assert len(items) == 1
    assert items[0]["brand"] == "Лукойл"


def test_freshness_flag(client, seeded):
    """ai92 у ГПН №2 старше 5 дней -> stale."""
    by = {i["name"]: i for i in client.get("/stations?fuel=ai92").json()}
    assert by["Лукойл №1"]["freshness"] == "fresh"
    assert by["ГПН №2"]["freshness"] == "stale"


def test_station_detail(client, seeded):
    items = client.get("/stations").json()
    sid = next(i["id"] for i in items if i["name"] == "Лукойл №1")
    d = client.get(f"/stations/{sid}").json()
    assert d["brand"] == "Лукойл"
    assert len(d["prices"]) == 2
    assert {p["fuel_type"] for p in d["prices"]} == {"ai92", "ai95"}
    # человекочитаемое имя топлива проставлено
    assert any(p["fuel_name"] == "АИ-95" for p in d["prices"])


def test_station_404(client, seeded):
    assert client.get("/stations/999999").status_code == 404


def test_refresh_throttled(client, monkeypatch):
    """Второй refresh подряд -> 429 (защита источника от долбёжки)."""
    monkeypatch.setattr(stations_router, "_last_refresh", None)
    monkeypatch.setattr(stations_router, "load_ivanovo", lambda db: (5, 10))

    first = client.post("/stations/refresh")
    assert first.status_code == 200
    assert first.json() == {"stations": 5, "prices": 10}

    second = client.post("/stations/refresh")
    assert second.status_code == 429
    assert "Retry-After" in second.headers
