from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Station, Price
from app.schemas import PricesSummary, FuelSummary
from app.services.fuel_codes import FUEL_TYPES
from app.services.gazprom_loader import (
    get_gazprom_availability_summary,
    get_gazprom_locations,
)

router = APIRouter(prefix="/prices", tags=["prices"])


@router.get("/summary", response_model=PricesSummary)
def prices_summary(db: Session = Depends(get_db)):
    """Сводка по городу: мин/средн/макс по каждому виду топлива."""
    rows = (
        db.query(
            Price.fuel_type,
            func.count(Price.id),
            func.min(Price.price),
            func.avg(Price.price),
            func.max(Price.price),
        )
        .group_by(Price.fuel_type)
        .all()
    )
    fuels = [
        FuelSummary(
            fuel_type=ft,
            fuel_name=FUEL_TYPES.get(ft, ft),
            count=cnt,
            min=round(mn, 2),
            avg=round(avg, 2),
            max=round(mx, 2),
        )
        for ft, cnt, mn, avg, mx in rows
    ]
    fuels.sort(key=lambda f: f.fuel_type)

    return PricesSummary(
        city="Иваново",
        stations=db.query(Station).count(),
        fuels=fuels,
        updated_at=db.query(func.max(Price.observed_at)).scalar(),
    )


@router.get("/gazprom/availability")
def gazprom_availability(db: Session = Depends(get_db)):
    """Статистика доступности топлива на АЗС Газпромнефти."""
    return get_gazprom_availability_summary(db)


@router.get("/gazprom/locations")
def gazprom_locations(db: Session = Depends(get_db)):
    """Все локации АЗС Газпромнефти с ценами и топливом."""
    locations = get_gazprom_locations(db)
    return {
        "count": len(locations),
        "stations": locations
    }


@router.get("/source")
def get_source():
    """Текущий источник данных."""
    from app.config import settings
    return {
        "source": settings.data_source,
        "available": ["russiabase", "cardoil"],
        "russiabase": {
            "pros": ["быстро", "полные данные", "встроено"],
            "cons": ["обновляется раз в 6 часов", "иногда неверное наличие"]
        },
        "cardoil": {
            "pros": ["более свежие данные", "точное наличие топлива"],
            "cons": ["требует Playwright", "медленнее"]
        }
    }


@router.get("/health")
def data_health(db: Session = Depends(get_db)):
    """Проверка здоровья данных."""
    from app.services.validator import health_check
    from app.models import Station
    
    stations = db.query(Station).all()
    return health_check(stations)


@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """Полная статистика по данным."""
    from app.services.stats import get_update_stats, get_brand_stats, get_fuel_availability
    
    return {
        'updates': get_update_stats(db),
        'brands': get_brand_stats(db),
        'fuel_availability': get_fuel_availability(db),
    }


@router.get("/history/{station_id}/{fuel_type}")
def price_history(station_id: int, fuel_type: str, days: int = 30, db: Session = Depends(get_db)):
    """История цен на топливо за период."""
    from datetime import datetime, timedelta
    from app.models_history import PriceHistory
    
    since = datetime.utcnow() - timedelta(days=days)
    
    history = db.query(PriceHistory).filter(
        PriceHistory.station_id == station_id,
        PriceHistory.fuel_type == fuel_type,
        PriceHistory.recorded_at >= since
    ).order_by(PriceHistory.recorded_at).all()
    
    return {
        "station_id": station_id,
        "fuel_type": fuel_type,
        "days": days,
        "points": [
            {"time": h.recorded_at.isoformat(), "price": h.price}
            for h in history
        ],
        "stats": {
            "current": history[-1].price if history else None,
            "min": min((h.price for h in history), default=None),
            "max": max((h.price for h in history), default=None),
            "avg": sum(h.price for h in history) / len(history) if history else None,
        } if history else None
    }
