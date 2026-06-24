"""Статистика о Газпромнефти из существующих источников.

Газпромнефть уже загружена из russiabase — здесь только
собираем статистику по наличию топлива и ценам.
"""
import logging
from sqlalchemy.orm import Session
from app.models import Station, Price

logger = logging.getLogger(__name__)


def _is_gazprom(brand: str) -> bool:
    """Проверка является ли бренд Газпромнефтью."""
    if not brand:
        return False
    return "газпром" in brand.lower()


def get_gazprom_availability_summary(db: Session) -> dict:
    """Статистика по доступности топлива на АЗС Газпромнефти.

    Returns:
        {
            "total_stations": 15,
            "fuel_types": {
                "ai92": {"stations": 15, "avg_price": 62.50, "min": 61.00, "max": 63.00},
                "ai95": {"stations": 14, "avg_price": 65.00},
                ...
            }
        }
    """
    all_stations = db.query(Station).all()
    gazprom_stations = [s for s in all_stations if _is_gazprom(s.brand)]

    total = len(gazprom_stations)
    if not total:
        logger.info("gazprom: станции не найдены")
        return {"total_stations": 0, "fuel_types": {}}

    # Собрать статистику по видам топлива
    fuel_stats = {}
    for station in gazprom_stations:
        for fuel_type in station.fuel_types or []:
            if fuel_type not in fuel_stats:
                fuel_stats[fuel_type] = {"stations": set(), "prices": []}

            fuel_stats[fuel_type]["stations"].add(station.id)

            # Найти цену для этого топлива
            price = db.query(Price).filter(
                Price.station_id == station.id,
                Price.fuel_type == fuel_type
            ).first()

            if price and price.price > 0:
                fuel_stats[fuel_type]["prices"].append(price.price)

    # Форматировать результат
    result = {
        "total_stations": total,
        "fuel_types": {}
    }

    for fuel_type, stats in fuel_stats.items():
        prices = stats["prices"]
        result["fuel_types"][fuel_type] = {
            "stations": len(stats["stations"]),
            "avg_price": round(sum(prices) / len(prices), 2) if prices else None,
            "min_price": round(min(prices), 2) if prices else None,
            "max_price": round(max(prices), 2) if prices else None,
        }

    return result


def get_gazprom_locations(db: Session) -> list[dict]:
    """Все АЗС Газпромнефти с информацией о топливе.

    Returns:
        Список станций с координатами и наличием топлива
    """
    all_stations = db.query(Station).all()
    gazprom_stations = [s for s in all_stations if _is_gazprom(s.brand)]

    result = []
    for st in gazprom_stations:
        result.append({
            "id": st.id,
            "name": st.name,
            "address": st.address,
            "lat": st.lat,
            "lon": st.lon,
            "fuel_types": st.fuel_types or [],
            "opening_hours": st.opening_hours,
            "prices": {
                p.fuel_type: p.price
                for p in st.prices
            }
        })

    return result
