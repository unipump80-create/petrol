#!/usr/bin/env python
"""Тест API endpoints."""
import sys
import json
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s — %(message)s"
)
logger = logging.getLogger(__name__)

# Инициализируем БД
logger.info("Инициализация БД...")
Base.metadata.create_all(bind=engine)

# Загружаем тестовые данные
from app.database import SessionLocal
from app.services.russiabase_loader import load_ivanovo
db = SessionLocal()
try:
    load_ivanovo(db)
finally:
    db.close()

# Тестируем API
client = TestClient(app)

logger.info("\n=== Тест /prices/summary ===")
resp = client.get("/prices/summary")
assert resp.status_code == 200
data = resp.json()
logger.info(f"Всего станций: {data['stations']}")
logger.info(f"Типов топлива: {len(data['fuels'])}")
for fuel in data["fuels"][:3]:
    logger.info(f"  {fuel['fuel_name']}: ср. {fuel['avg']} (min={fuel['min']}, max={fuel['max']})")

logger.info("\n=== Тест /prices/gazprom/availability ===")
resp = client.get("/prices/gazprom/availability")
assert resp.status_code == 200
data = resp.json()
logger.info(f"Станций Газпромнефти: {data['total_stations']}")
for fuel_type, info in sorted(data["fuel_types"].items()):
    logger.info(
        f"  {fuel_type}: {info['stations']} станций, "
        f"ср. {info['avg_price']} руб/л"
    )

logger.info("\n=== Тест /prices/gazprom/locations ===")
resp = client.get("/prices/gazprom/locations")
assert resp.status_code == 200
data = resp.json()
logger.info(f"Локаций: {data['count']}")

if data["count"] > 0:
    loc = data["stations"][0]
    logger.info(f"\nПример первой локации:")
    logger.info(f"  {loc['name']}")
    logger.info(f"  {loc['address']}")
    logger.info(f"  Координаты: {loc['lat']:.4f}, {loc['lon']:.4f}")
    logger.info(f"  Топливо: {', '.join(loc['fuel_types'])}")
    logger.info(f"  Цены: {json.dumps(loc['prices'], indent=4)}")

logger.info("\n✓ Все тесты пройдены!")
