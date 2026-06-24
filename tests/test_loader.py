"""Тесты загрузчика russiabase (сеть замокана)."""
import app.services.russiabase_loader as loader
from app.models import Station, Price


def test_load_dedup_gas_propan(db_session, monkeypatch):
    """gas и propan оба -> 'gas': одна цена на станцию, без IntegrityError."""
    record = {
        "poiid": 100, "name": "Газойл №1", "address": "г. Иваново",
        "ai92": "54.0", "gas": "30.0", "propan": "31.0",  # оба газовых поля
        "prices_updated": "01.06.2026",
    }
    monkeypatch.setattr(loader, "fetch_ivanovo", lambda: ([record], {}))

    ns, npr = loader.load_ivanovo(db_session)

    assert ns == 1
    gas_prices = db_session.query(Price).filter_by(fuel_type="gas").all()
    assert len(gas_prices) == 1            # не задублировалось
    assert gas_prices[0].price == 30.0     # выиграло поле gas (идёт первым)


def test_load_propan_only(db_session, monkeypatch):
    """Только propan заполнен -> цена газа всё равно есть."""
    record = {
        "poiid": 101, "name": "ГАЗ №2", "address": "г. Иваново",
        "propan": "28.5", "prices_updated": "01.06.2026",
    }
    monkeypatch.setattr(loader, "fetch_ivanovo", lambda: ([record], {}))

    loader.load_ivanovo(db_session)
    gas = db_session.query(Price).filter_by(fuel_type="gas").one()
    assert gas.price == 28.5


def test_load_skips_zero_and_bad_prices(db_session, monkeypatch):
    record = {
        "poiid": 102, "name": "АЗС", "address": "г. Иваново",
        "ai92": "0", "ai95": "", "ai98": "хлам", "dt": "55.5",
        "prices_updated": "01.06.2026",
    }
    monkeypatch.setattr(loader, "fetch_ivanovo", lambda: ([record], {}))

    loader.load_ivanovo(db_session)
    codes = {p.fuel_type for p in db_session.query(Price).all()}
    assert codes == {"diesel"}  # только валидная цена


def test_load_removes_stale_stations(db_session, monkeypatch):
    """АЗС, пропавшая из источника, удаляется вместе с ценами."""
    old = Station(poiid="999", brand="Старая", name="Old", address="г. Иваново")
    db_session.add(old)
    db_session.commit()

    record = {"poiid": 1, "name": "Новая", "address": "г. Иваново",
              "ai92": "50.0", "prices_updated": "01.06.2026"}
    monkeypatch.setattr(loader, "fetch_ivanovo", lambda: ([record], {}))

    loader.load_ivanovo(db_session)
    poiids = {s.poiid for s in db_session.query(Station).all()}
    assert poiids == {"1"}  # старая удалена


def test_load_skips_empty_stations(db_session, monkeypatch):
    """АЗС без цен (закрытые/ошибка) не загружаются."""
    records = [
        {"poiid": "1", "name": "OK", "address": "г. Иваново", "ai92": "50.0", "prices_updated": "01.06.2026"},
        {"poiid": "2", "name": "Закрытая", "address": "г. Иваново", "prices_updated": "01.06.2026"},  # нет цен
    ]
    monkeypatch.setattr(loader, "fetch_ivanovo", lambda: (records, {}))

    loader.load_ivanovo(db_session)
    poiids = {s.poiid for s in db_session.query(Station).all()}
    assert "2" not in poiids  # без цен не загрузилась
    assert "1" in poiids  # с ценой загрузилась
