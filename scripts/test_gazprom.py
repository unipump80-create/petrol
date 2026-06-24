#!/usr/bin/env python
"""Тест доступности топлива на АЗС Газпромнефти."""
import sys
import logging
from pathlib import Path

# Добавляем корень проекта в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal, Base, engine
from app.services.russiabase_loader import load_ivanovo
from app.services.gazprom_loader import (
    get_gazprom_availability_summary,
    get_gazprom_locations,
)
from app.models import Station

logging.basicConfig(
    level=logging.INFO,
    format="%(name)s — %(levelname)s — %(message)s"
)
logger = logging.getLogger(__name__)


def test_load_russiabase():
    """Загрузить данные из russiabase (содержит Газпромнефть)."""
    logger.info("=== Загрузка данных из russiabase ===")
    db = SessionLocal()
    try:
        ns, np = load_ivanovo(db)
        logger.info(f"✓ Загружено: {ns} станций, {np} цен")
    finally:
        db.close()


def test_gazprom_stats():
    """Статистика по Газпромнефти."""
    logger.info("=== Статистика Газпромнефти ===")
    db = SessionLocal()
    try:
        # Общая статистика
        stats = get_gazprom_availability_summary(db)
        logger.info(f"Найдено {stats['total_stations']} станций Газпромнефти\n")

        if stats["total_stations"] > 0:
            logger.info("Доступность топлива по типам:")
            for fuel, data in sorted(stats.get("fuel_types", {}).items()):
                logger.info(
                    f"  {fuel:10s}: {data['stations']:2d} станций, "
                    f"ср. {data['avg_price']:6.2f} руб/л "
                    f"({data['min_price']:.2f}-{data['max_price']:.2f})"
                )

    finally:
        db.close()


def test_gazprom_locations():
    """JSON с локациями Газпромнефти."""
    logger.info("=== Локации АЗС Газпромнефти ===")
    db = SessionLocal()
    try:
        locations = get_gazprom_locations(db)
        logger.info(f"Получено {len(locations)} локаций\n")

        if locations:
            logger.info("Примеры станций:")
            for loc in locations[:3]:
                logger.info(f"\n  • {loc['name']}")
                logger.info(f"    адрес: {loc['address']}")
                logger.info(f"    координаты: {loc['lat']:.4f}, {loc['lon']:.4f}")
                logger.info(f"    топливо: {', '.join(loc['fuel_types'])}")
                prices_str = ", ".join(f"{k}={v:.2f}" for k, v in loc['prices'].items())
                logger.info(f"    цены: {prices_str}")

    finally:
        db.close()


if __name__ == "__main__":
    # Инициализируем БД
    logger.info("=== Инициализация БД ===")
    Base.metadata.create_all(bind=engine)
    logger.info("✓ БД готова\n")

    test_load_russiabase()
    print()
    test_gazprom_stats()
    print()
    test_gazprom_locations()
