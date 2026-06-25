"""Жёсткие тесты авто-миграции схемы (_auto_migrate)."""
import sqlite3

import pytest
from sqlalchemy import create_engine, inspect, text

import app.main as main_mod
from app.database import Base


@pytest.fixture
def temp_engine(tmp_path):
    """Временная файловая SQLite + подмена engine в app.main."""
    dbfile = tmp_path / "t.db"
    eng = create_engine(f"sqlite:///{dbfile}")
    orig = main_mod.engine
    main_mod.engine = eng
    try:
        yield eng, str(dbfile)
    finally:
        main_mod.engine = orig
        eng.dispose()


def _make_old_fuel_reports(dbfile):
    con = sqlite3.connect(dbfile)
    con.execute("CREATE TABLE fuel_reports (id INTEGER PRIMARY KEY, "
                "station_id INTEGER, fuel_type TEXT, available BOOLEAN, created_at TEXT)")
    con.execute("INSERT INTO fuel_reports (station_id, fuel_type, available) "
                "VALUES (1,'ai95',0)")
    con.commit(); con.close()


def test_migrate_old_fuel_reports_recreated(temp_engine):
    eng, dbfile = temp_engine
    _make_old_fuel_reports(dbfile)
    main_mod._auto_migrate()
    Base.metadata.create_all(bind=eng)
    cols = {c["name"] for c in inspect(eng).get_columns("fuel_reports")}
    assert "status" in cols
    assert "available" not in cols


def test_migrate_adds_missing_station_column(temp_engine):
    """Старая stations без benzuber_fuels -> колонка добавляется."""
    eng, dbfile = temp_engine
    con = sqlite3.connect(dbfile)
    # минимальная старая схема stations без benzuber_fuels
    con.execute("CREATE TABLE stations (id INTEGER PRIMARY KEY, poiid TEXT, "
                "brand TEXT, name TEXT, lat REAL, lon REAL, fuel_types TEXT)")
    con.execute("INSERT INTO stations (poiid, brand, lat, lon) VALUES ('1','Лукойл',57.0,40.9)")
    con.commit(); con.close()

    main_mod._auto_migrate()
    cols = {c["name"] for c in inspect(eng).get_columns("stations")}
    assert "benzuber_fuels" in cols
    assert "opening_hours" in cols
    # данные не потеряны
    with eng.connect() as conn:
        n = conn.execute(text("SELECT count(*) FROM stations")).scalar()
    assert n == 1


def test_migrate_idempotent(temp_engine):
    """Повторный прогон не падает и ничего не ломает."""
    eng, dbfile = temp_engine
    _make_old_fuel_reports(dbfile)
    main_mod._auto_migrate(); Base.metadata.create_all(bind=eng)
    main_mod._auto_migrate(); Base.metadata.create_all(bind=eng)  # второй раз
    cols = {c["name"] for c in inspect(eng).get_columns("fuel_reports")}
    assert "status" in cols


def test_migrate_fresh_db_no_error(temp_engine):
    """Пустая БД без таблиц — миграция не падает."""
    main_mod._auto_migrate()  # таблиц нет — просто no-op
    eng, _ = temp_engine
    Base.metadata.create_all(bind=eng)
    assert "stations" in inspect(eng).get_table_names()


def test_migrate_current_schema_untouched(temp_engine):
    """На актуальной схеме миграция ничего не ломает."""
    eng, _ = temp_engine
    Base.metadata.create_all(bind=eng)  # сразу актуальная
    main_mod._auto_migrate()
    cols = {c["name"] for c in inspect(eng).get_columns("stations")}
    assert "benzuber_fuels" in cols
    rcols = {c["name"] for c in inspect(eng).get_columns("fuel_reports")}
    assert "status" in rcols
