from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload
from app.database import get_db
from app.models import Station, Price
from app.schemas import StationOut, StationListItem, PriceOut
from app.services.fuel_codes import FUEL_TYPES
from app.services.russiabase_loader import load_ivanovo
from app.config import settings
from app.utils import utcnow

router = APIRouter(prefix="/stations", tags=["stations"])

# Троттлинг refresh: не парсить источник чаще, чем раз в N секунд (на весь сервер).
# Защита от злоупотребления — иначе любой может дёргать парсер в цикле.
_last_refresh: datetime | None = None


@router.post("/refresh")
def refresh(db: Session = Depends(get_db)):
    """Ручное обновление данных из источника (с троттлингом)."""
    global _last_refresh
    now = utcnow()
    if _last_refresh is not None:
        elapsed = (now - _last_refresh).total_seconds()
        if elapsed < settings.refresh_min_interval:
            retry = int(settings.refresh_min_interval - elapsed)
            raise HTTPException(
                status_code=429,
                detail=f"Слишком часто. Повторите через {retry} с.",
                headers={"Retry-After": str(retry)},
            )
    _last_refresh = now
    ns, npr = load_ivanovo(db)
    return {"stations": ns, "prices": npr}

# Пороги свежести данных (дни)
FRESH_DAYS = 1
RECENT_DAYS = 5


def freshness_of(observed_at: datetime | None) -> tuple[int | None, str | None]:
    """Возвращает (дней_назад, статус: fresh|recent|stale)."""
    if observed_at is None:
        return None, None
    days = (utcnow() - observed_at).days
    if days <= FRESH_DAYS:
        status = "fresh"
    elif days <= RECENT_DAYS:
        status = "recent"
    else:
        status = "stale"
    return days, status


@router.get("", response_model=list[StationListItem])
def list_stations(
    db: Session = Depends(get_db),
    fuel: str | None = Query(None, description="Код топлива: ai92, ai95, diesel, gas…"),
    brand: str | None = Query(None, description="Фильтр по бренду"),
    sort: str = Query("price", description="price | name"),
):
    """Список АЗС. При указании fuel — с ценой и сортировкой по ней."""
    query = db.query(Station).options(selectinload(Station.prices))
    if brand:
        query = query.filter(Station.brand == brand)
    stations = query.all()

    items: list[StationListItem] = []
    for st in stations:
        price = None
        observed = None
        available = True
        if fuel:
            match = next((p for p in st.prices if p.fuel_type == fuel), None)
            if match is None:
                available = False  # не продаёт это топливо — покажем серым
            else:
                price = match.price
                observed = match.observed_at
        elif st.prices:
            dates = [p.observed_at for p in st.prices if p.observed_at]
            observed = max(dates) if dates else None
        days_old, fresh = freshness_of(observed)
        items.append(StationListItem(
            id=st.id, brand=st.brand, name=st.name, address=st.address,
            lat=st.lat, lon=st.lon, fuel_types=st.fuel_types, price=price,
            available=available, observed_at=observed, days_old=days_old,
            freshness=fresh,
        ))

    if fuel and sort == "price":
        items.sort(key=lambda x: (x.price is None, x.price))
    elif sort == "name":
        items.sort(key=lambda x: (x.name or "").lower())
    return items


@router.get("/{station_id}", response_model=StationOut)
def get_station(station_id: int, db: Session = Depends(get_db)):
    """Детали АЗС со всеми ценами."""
    st = db.query(Station).options(selectinload(Station.prices)).filter(
        Station.id == station_id).first()
    if st is None:
        raise HTTPException(status_code=404, detail="АЗС не найдена")
    prices = [
        PriceOut(fuel_type=p.fuel_type,
                 fuel_name=FUEL_TYPES.get(p.fuel_type, p.fuel_type),
                 price=p.price, observed_at=p.observed_at)
        for p in st.prices
    ]
    return StationOut(
        id=st.id, brand=st.brand, name=st.name, address=st.address,
        lat=st.lat, lon=st.lon, opening_hours=st.opening_hours,
        fuel_types=st.fuel_types, prices=prices,
    )
