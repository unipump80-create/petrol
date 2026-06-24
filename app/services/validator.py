"""Валидация и очистка данных о АЗС и ценах."""
import logging
from typing import Optional
from app.models import Station, Price

logger = logging.getLogger(__name__)


def validate_station(station: Station) -> bool:
    """Проверить корректность данных о станции."""
    checks = [
        ('name', station.name and len(station.name) > 0),
        ('lat', station.lat and -90 <= station.lat <= 90),
        ('lon', station.lon and -180 <= station.lon <= 180),
        ('brand', station.brand and len(station.brand) > 0),
        ('fuel_types', station.fuel_types and len(station.fuel_types) > 0),
    ]

    for field, is_valid in checks:
        if not is_valid:
            logger.warning(f"station validation: {station.poiid} - invalid {field}")
            return False

    return True


def validate_price(price: Price) -> bool:
    """Проверить корректность цены."""
    checks = [
        ('price', price.price and 10 < price.price < 300),  # разумный диапазон руб/л
        ('fuel_type', price.fuel_type and price.fuel_type in [
            'ai92', 'ai95', 'ai98', 'ai100', 'diesel', 'gas', 'ai95plus'
        ]),
    ]

    for field, is_valid in checks:
        if not is_valid:
            logger.debug(f"price validation: {price.station_id}/{price.fuel_type} - invalid {field}")
            return False

    return True


def clean_stations(stations: list[Station]) -> list[Station]:
    """Удалить невалидные станции и цены."""
    valid = []

    for station in stations:
        if not validate_station(station):
            continue

        # Проверяем цены
        valid_prices = [p for p in station.prices if validate_price(p)]

        if not valid_prices:
            logger.debug(f"station {station.poiid}: no valid prices, skipping")
            continue

        # Обновляем станцию только с валидными ценами
        station.prices = valid_prices
        valid.append(station)

    logger.info(f"cleaned: {len(stations)} → {len(valid)} valid stations")
    return valid


def detect_duplicates(stations: list[Station]) -> dict:
    """Найти возможные дубликаты по координатам."""
    duplicates = {}

    for i, s1 in enumerate(stations):
        if not s1.lat or not s1.lon:
            continue

        for s2 in stations[i+1:]:
            if not s2.lat or not s2.lon:
                continue

            # Расстояние в км (приблизительно)
            lat_diff = abs(s1.lat - s2.lat) * 111
            lon_diff = abs(s1.lon - s2.lon) * 111 * 0.85

            distance = (lat_diff**2 + lon_diff**2) ** 0.5

            if distance < 0.1:  # менее 100 метров
                key = f"{s1.poiid}-{s2.poiid}"
                duplicates[key] = {
                    'station1': s1.name,
                    'station2': s2.name,
                    'distance_m': int(distance * 1000),
                }

    if duplicates:
        logger.warning(f"found {len(duplicates)} potential duplicates")

    return duplicates


def health_check(stations: list[Station]) -> dict:
    """Проверка здоровья данных."""
    total = len(stations)
    with_prices = sum(1 for s in stations if s.prices)
    with_coords = sum(1 for s in stations if s.lat and s.lon)
    with_address = sum(1 for s in stations if s.address)

    fuels = set()
    for station in stations:
        fuels.update(station.fuel_types or [])

    return {
        'total_stations': total,
        'with_prices': with_prices,
        'with_coordinates': with_coords,
        'with_address': with_address,
        'unique_fuels': sorted(list(fuels)),
        'health_score': (with_prices + with_coords + with_address) / (total * 3) if total else 0,
    }
