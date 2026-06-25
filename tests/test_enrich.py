"""Жёсткие тесты обогащения наличия: card-oil (источник истины) + Benzuber."""
import app.services.cardoil_loader as cardoil
import app.services.benzuber_loader as benzuber
from app.models import Station


def _station(db, poiid, brand, lat, lon, fuels):
    s = Station(poiid=poiid, brand=brand, name=poiid, lat=lat, lon=lon,
                fuel_types=fuels)
    db.add(s); db.flush()
    return s


# ---------- card-oil: источник истины наличия ----------

def test_cardoil_overwrites_matched(db_session, monkeypatch):
    """Совпадение бренд+<150м -> fuel_types перезаписывается данными card-oil."""
    s = _station(db_session, "1", "Лукойл", 57.0, 40.9, ["ai92", "ai95", "ai95plus"])
    db_session.commit()
    monkeypatch.setattr(cardoil, "fetch_cardoil_points", lambda bbox=None: [
        {"poiid": "cardoil_x", "brand": "Лукойл", "lat": 57.0004, "lon": 40.9,
         "fuel_types": ["ai92", "diesel"]},  # ~44м, другой набор
    ])
    stats = cardoil.enrich_availability(db_session)
    assert stats["matched"] == 1
    db_session.refresh(s)
    assert s.fuel_types == ["ai92", "diesel"]   # перезаписано card-oil


def test_cardoil_skips_far(db_session, monkeypatch):
    """Та же марка, но >150м -> наличие не трогаем."""
    s = _station(db_session, "1", "Лукойл", 57.0, 40.9, ["ai92", "ai95"])
    db_session.commit()
    monkeypatch.setattr(cardoil, "fetch_cardoil_points", lambda bbox=None: [
        {"poiid": "cardoil_x", "brand": "Лукойл", "lat": 57.005, "lon": 40.9,
         "fuel_types": ["diesel"]},  # ~550м
    ])
    cardoil.enrich_availability(db_session)
    db_session.refresh(s)
    assert s.fuel_types == ["ai92", "ai95"]     # не тронуто


def test_cardoil_skips_other_brand(db_session, monkeypatch):
    """Рядом, но другой бренд -> не матчим."""
    s = _station(db_session, "1", "Лукойл", 57.0, 40.9, ["ai92"])
    db_session.commit()
    monkeypatch.setattr(cardoil, "fetch_cardoil_points", lambda bbox=None: [
        {"poiid": "cardoil_x", "brand": "Газпромнефть", "lat": 57.0, "lon": 40.9,
         "fuel_types": ["ai95"]},
    ])
    stats = cardoil.enrich_availability(db_session)
    assert stats["matched"] == 0
    db_session.refresh(s)
    assert s.fuel_types == ["ai92"]


# ---------- Benzuber: кросс-чек (только положительный) ----------

def test_benzuber_sets_fuels_on_match(db_session, monkeypatch):
    s = _station(db_session, "1", "Газпромнефть", 57.0, 40.9, ["ai92", "ai95"])
    db_session.commit()
    monkeypatch.setattr(benzuber, "fetch_benzuber_ivanovo", lambda: [
        {"brand": "Газпромнефть", "lat": 57.0003, "lon": 40.9,
         "fuels": ["ai95", "diesel"]},
    ])
    stats = benzuber.load_benzuber(db_session)
    assert stats["matched"] == 1
    db_session.refresh(s)
    assert set(s.benzuber_fuels) == {"ai95", "diesel"}


def test_benzuber_none_when_no_match(db_session, monkeypatch):
    s = _station(db_session, "1", "Газпромнефть", 57.0, 40.9, ["ai92"])
    db_session.commit()
    monkeypatch.setattr(benzuber, "fetch_benzuber_ivanovo", lambda: [
        {"brand": "Газпромнефть", "lat": 57.05, "lon": 40.9, "fuels": ["ai95"]},
    ])
    benzuber.load_benzuber(db_session)
    db_session.refresh(s)
    assert s.benzuber_fuels is None


def test_benzuber_confirms_positive_only(client, db_session):
    """benzuber_confirms=True только если выбранный вид в benzuber_fuels."""
    s = _station(db_session, "1", "Газпромнефть", 57.0, 40.9, ["ai92", "ai95"])
    s.benzuber_fuels = ["ai95"]
    from app.models import Price
    db_session.add(Price(station_id=s.id, fuel_type="ai95", price=60.0))
    db_session.commit()

    by95 = next(x for x in client.get("/stations?fuel=ai95").json() if x["id"] == s.id)
    by92 = next(x for x in client.get("/stations?fuel=ai92").json() if x["id"] == s.id)
    assert by95["benzuber_confirms"] is True
    assert by92["benzuber_confirms"] is False
