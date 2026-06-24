"""Статистика и мониторинг обновлений."""
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models import Station, Price

logger = logging.getLogger(__name__)


def get_update_stats(db: Session) -> dict:
    """Статистика по времени обновления цен."""
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    six_hours_ago = datetime.utcnow() - timedelta(hours=6)
    one_day_ago = datetime.utcnow() - timedelta(days=1)

    fresh = db.query(func.count(Price.id)).filter(
        Price.observed_at >= one_hour_ago
    ).scalar() or 0

    recent = db.query(func.count(Price.id)).filter(
        Price.observed_at >= six_hours_ago,
        Price.observed_at < one_hour_ago
    ).scalar() or 0

    stale = db.query(func.count(Price.id)).filter(
        Price.observed_at >= one_day_ago,
        Price.observed_at < six_hours_ago
    ).scalar() or 0

    very_old = db.query(func.count(Price.id)).filter(
        Price.observed_at < one_day_ago
    ).scalar() or 0

    total_prices = fresh + recent + stale + very_old

    return {
        'fresh_1h': fresh,
        'recent_6h': recent,
        'stale_24h': stale,
        'very_old': very_old,
        'total': total_prices,
        'freshness_percent': round(fresh / total_prices * 100, 1) if total_prices else 0,
    }


def get_brand_stats(db: Session) -> dict:
    """Статистика по брендам."""
    stats = {}

    brands = db.query(Station.brand, func.count(Station.id)).group_by(Station.brand).all()

    for brand, count in brands:
        if not brand:
            continue

        prices = db.query(func.count(Price.id)).filter(
            Station.brand == brand,
            Price.station_id == Station.id
        ).scalar() or 0

        stats[brand] = {
            'stations': count,
            'prices': prices,
        }

    return dict(sorted(stats.items(), key=lambda x: x[1]['stations'], reverse=True))


def get_fuel_availability(db: Session) -> dict:
    """Какое топливо доступно на какой процент станций."""
    all_stations = db.query(Station).all()
    total = len(all_stations)

    if not total:
        return {}

    fuel_counts = {}

    for station in all_stations:
        for fuel in station.fuel_types or []:
            if fuel not in fuel_counts:
                fuel_counts[fuel] = 0
            fuel_counts[fuel] += 1

    return {
        fuel: round(count / total * 100, 1)
        for fuel, count in sorted(fuel_counts.items(), key=lambda x: x[1], reverse=True)
    }
