"""Тесты вспомогательных сервисов: коды топлива, парсинг дат, свежесть."""
from datetime import datetime, timedelta

import pytest

from app.services.fuel_codes import osm_fuels_from_tags, RUSSIABASE_MAP, FUEL_TYPES
from app.services.russiabase_loader import _parse_date
from app.routers.stations import freshness_of


# ---- OSM теги топлива ----

def test_osm_fuels_basic():
    tags = {"fuel:octane_92": "yes", "fuel:octane_95": "yes", "fuel:diesel": "yes"}
    assert osm_fuels_from_tags(tags) == ["ai92", "ai95", "diesel"]


def test_osm_fuels_ignores_no():
    tags = {"fuel:octane_95": "no", "fuel:diesel": "yes"}
    assert osm_fuels_from_tags(tags) == ["diesel"]


def test_osm_fuels_lpg_cng_both_gas():
    assert osm_fuels_from_tags({"fuel:lpg": "yes", "fuel:cng": "yes"}) == ["gas"]


def test_osm_fuels_empty():
    assert osm_fuels_from_tags({"amenity": "fuel"}) == []


# ---- маппинг полон ----

def test_every_russiabase_code_has_name():
    for code in RUSSIABASE_MAP.values():
        assert code in FUEL_TYPES, f"код {code} без человекочитаемого имени"


# ---- парсинг дат ----

def test_parse_date_valid():
    assert _parse_date("15.03.2026") == datetime(2026, 3, 15)


def test_parse_date_invalid_falls_back_to_now():
    before = datetime.utcnow()
    result = _parse_date("не дата")
    assert result >= before


def test_parse_date_none_falls_back_to_now():
    before = datetime.utcnow()
    assert _parse_date(None) >= before


# ---- свежесть ----

def test_freshness_none():
    assert freshness_of(None) == (None, None)


def test_freshness_fresh():
    days, status = freshness_of(datetime.utcnow())
    assert days == 0
    assert status == "fresh"


def test_freshness_recent():
    _, status = freshness_of(datetime.utcnow() - timedelta(days=3))
    assert status == "recent"


def test_freshness_stale():
    _, status = freshness_of(datetime.utcnow() - timedelta(days=20))
    assert status == "stale"
