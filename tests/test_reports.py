"""Жёсткие тесты краудсорс-репортов наличия (3 статуса, TTL, изоляция)."""
from datetime import datetime, timedelta

import pytest

from app.models import FuelReport, Station
from app.config import settings


def _avail(client, station_id, fuel="ai95"):
    """Вернуть запись станции из /stations?fuel=... по id."""
    data = client.get(f"/stations?fuel={fuel}").json()
    return next(x for x in data if x["id"] == station_id)


# ---------- валидация входа ----------

def test_report_valid_statuses(client, seeded):
    sid = seeded.query(Station).filter_by(poiid="1").one().id
    for status in ("in_stock", "out_of_stock", "unavailable"):
        r = client.post(f"/stations/{sid}/report",
                        json={"fuel_type": "ai95", "status": status})
        assert r.status_code == 200, status
        assert r.json()["report"]["status"] == status


def test_report_bad_status(client, seeded):
    sid = seeded.query(Station).filter_by(poiid="1").one().id
    r = client.post(f"/stations/{sid}/report",
                    json={"fuel_type": "ai95", "status": "maybe"})
    assert r.status_code == 400


def test_report_bad_fuel(client, seeded):
    sid = seeded.query(Station).filter_by(poiid="1").one().id
    r = client.post(f"/stations/{sid}/report",
                    json={"fuel_type": "kerosene", "status": "in_stock"})
    assert r.status_code == 400


def test_report_missing_station(client, seeded):
    r = client.post("/stations/999999/report",
                    json={"fuel_type": "ai95", "status": "out_of_stock"})
    assert r.status_code == 404


def test_report_missing_body_field(client, seeded):
    sid = seeded.query(Station).filter_by(poiid="1").one().id
    r = client.post(f"/stations/{sid}/report", json={"fuel_type": "ai95"})
    assert r.status_code == 422  # pydantic: нет status


# ---------- влияние на наличие ----------

def test_out_of_stock_makes_unavailable(client, seeded):
    sid = seeded.query(Station).filter_by(poiid="1").one().id
    assert _avail(client, sid)["available"] is True
    client.post(f"/stations/{sid}/report",
                json={"fuel_type": "ai95", "status": "out_of_stock"})
    row = _avail(client, sid)
    assert row["available"] is False
    assert row["report_status"] == "out_of_stock"


def test_unavailable_makes_unavailable(client, seeded):
    sid = seeded.query(Station).filter_by(poiid="1").one().id
    client.post(f"/stations/{sid}/report",
                json={"fuel_type": "ai95", "status": "unavailable"})
    assert _avail(client, sid)["available"] is False


def test_in_stock_keeps_available(client, seeded):
    sid = seeded.query(Station).filter_by(poiid="1").one().id
    client.post(f"/stations/{sid}/report",
                json={"fuel_type": "ai95", "status": "in_stock"})
    row = _avail(client, sid)
    assert row["available"] is True
    assert row["report_status"] == "in_stock"


def test_latest_report_wins(client, seeded):
    """out_of_stock затем in_stock -> побеждает последний."""
    sid = seeded.query(Station).filter_by(poiid="1").one().id
    client.post(f"/stations/{sid}/report",
                json={"fuel_type": "ai95", "status": "out_of_stock"})
    client.post(f"/stations/{sid}/report",
                json={"fuel_type": "ai95", "status": "in_stock"})
    row = _avail(client, sid)
    assert row["report_status"] == "in_stock"
    assert row["available"] is True
    assert row["report_count"] == 2


# ---------- изоляция: по топливу и по станции ----------

def test_report_isolated_by_fuel(client, seeded):
    """Репорт по ai95 не влияет на выдачу ai92."""
    sid = seeded.query(Station).filter_by(poiid="1").one().id
    client.post(f"/stations/{sid}/report",
                json={"fuel_type": "ai95", "status": "out_of_stock"})
    assert _avail(client, sid, "ai95")["available"] is False
    assert _avail(client, sid, "ai92")["available"] is True
    assert _avail(client, sid, "ai92")["report_status"] is None


def test_report_isolated_by_station(client, seeded):
    s1 = seeded.query(Station).filter_by(poiid="1").one().id
    client.post(f"/stations/{s1}/report",
                json={"fuel_type": "ai92", "status": "out_of_stock"})
    s2 = seeded.query(Station).filter_by(poiid="2").one().id
    assert _avail(client, s2, "ai92")["report_status"] is None


# ---------- TTL ----------

def _insert_report(db, station_id, fuel, status, age_hours):
    db.add(FuelReport(station_id=station_id, fuel_type=fuel, status=status,
                      created_at=datetime.utcnow() - timedelta(hours=age_hours)))
    db.commit()


def test_report_expires_after_ttl(client, seeded):
    sid = seeded.query(Station).filter_by(poiid="1").one().id
    _insert_report(seeded, sid, "ai95", "out_of_stock",
                   age_hours=settings.report_ttl_hours + 1)
    row = _avail(client, sid)
    assert row["report_status"] is None       # протух — игнор
    assert row["available"] is True           # вернулось каталожное наличие


def test_report_within_ttl_counts(client, seeded):
    sid = seeded.query(Station).filter_by(poiid="1").one().id
    _insert_report(seeded, sid, "ai95", "out_of_stock",
                   age_hours=settings.report_ttl_hours - 0.5)
    row = _avail(client, sid)
    assert row["report_status"] == "out_of_stock"
    assert row["available"] is False


def test_fresh_overrides_expired(client, seeded):
    """Свежий in_stock важнее старого out_of_stock."""
    sid = seeded.query(Station).filter_by(poiid="1").one().id
    _insert_report(seeded, sid, "ai95", "out_of_stock",
                   age_hours=settings.report_ttl_hours + 2)  # протух
    _insert_report(seeded, sid, "ai95", "in_stock", age_hours=0.1)  # свежий
    row = _avail(client, sid)
    assert row["report_status"] == "in_stock"
    assert row["report_count"] == 1           # протухший не считается
