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
