"""Общая инфраструктура тестов: изолированная in-memory БД + TestClient."""
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import Station, Price
from app.services import cache as _cache


@pytest.fixture(autouse=True)
def _clear_cache():
    """Глобальный in-memory кэш не должен протекать между тестами."""
    _cache.cache_clear()
    yield
    _cache.cache_clear()


@pytest.fixture
def db_session():
    """Чистая in-memory SQLite на каждый тест."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # один коннект на всё время — иначе :memory: пуста
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def client(db_session):
    """TestClient, подключённый к тестовой БД."""
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def seeded(db_session):
    """Три АЗС: с ai95+ai92, только ai92, и без цен. Возвращает session."""
    now = datetime.utcnow()
    s1 = Station(poiid="1", brand="Лукойл", name="Лукойл №1",
                 address="г. Иваново, ул. А", lat=57.0, lon=40.9,
                 fuel_types=["ai92", "ai95"])
    s2 = Station(poiid="2", brand="Газпромнефть", name="ГПН №2",
                 address="г. Иваново, ул. Б", lat=57.01, lon=40.95,
                 fuel_types=["ai92"])
    s3 = Station(poiid="3", brand="Татнефть", name="ТН №3",
                 address="г. Иваново, ул. В", lat=57.02, lon=40.97,
                 fuel_types=[])
    db_session.add_all([s1, s2, s3])
    db_session.flush()
    db_session.add_all([
        Price(station_id=s1.id, fuel_type="ai95", price=58.50, observed_at=now),
        Price(station_id=s1.id, fuel_type="ai92", price=54.20, observed_at=now),
        Price(station_id=s2.id, fuel_type="ai92", price=53.90,
              observed_at=now - timedelta(days=10)),
    ])
    db_session.commit()
    return db_session
