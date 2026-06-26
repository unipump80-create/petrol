import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload
from app.database import get_db
from app.models import Station, Price, FuelReport
from app.schemas import StationOut, StationListItem, PriceOut, ReportIn, REPORT_STATUSES
from app.services.fuel_codes import FUEL_TYPES
from app.services.russiabase_loader import load_ivanovo
from app.services.cardoil_loader import enrich_availability
from app.services.cache import cache_clear
from app.config import settings
from app.utils import utcnow

router = APIRouter(prefix="/stations", tags=["stations"])
logger = logging.getLogger(__name__)


def _recent_reports(db: Session, fuel: str) -> dict[int, dict]:
    """Свежие краудсорс-репорты по виду топлива: {station_id: {status, at, count}}.

    status (последний репорт за report_ttl_hours):
      in_stock | out_of_stock | unavailable  (модель ATAN/rk.gov)
    """
    if not fuel:
        return {}
    since = utcnow() - timedelta(hours=settings.report_ttl_hours)
    rows = (
        db.query(FuelReport)
        .filter(FuelReport.fuel_type == fuel, FuelReport.created_at >= since)
        .order_by(FuelReport.created_at.asc())
        .all()
    )
    by_station: dict[int, dict] = {}
    for r in rows:
        cur = by_station.setdefault(r.station_id, {"count": 0, "at": None, "status": None})
        cur["count"] += 1
        cur["at"] = r.created_at         # последний по времени (rows отсортированы asc)
        cur["status"] = r.status
    return by_station


@router.post("/{station_id}/report")
def report_fuel(station_id: int, body: ReportIn, db: Session = Depends(get_db)):
    """Краудсорс-репорт о наличии топлива (есть/кончился/не продаётся)."""
    if body.fuel_type not in FUEL_TYPES:
        raise HTTPException(status_code=400, detail="Неизвестный вид топлива")
    if body.status not in REPORT_STATUSES:
        raise HTTPException(status_code=400, detail="Неизвестный статус")
    st = db.query(Station).filter(Station.id == station_id).first()
    if st is None:
        raise HTTPException(status_code=404, detail="АЗС не найдена")
    db.add(FuelReport(station_id=station_id, fuel_type=body.fuel_type,
                      status=body.status))
    db.commit()
    rep = _recent_reports(db, body.fuel_type).get(station_id, {})
    return {"ok": True, "station_id": station_id, "fuel_type": body.fuel_type,
            "report": rep}

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
    enrich = {}
    try:
        enrich = enrich_availability(db)
    except Exception:
        pass  # наличие останется из russiabase
    gdebenz = {}
    try:
        from app.services.gdebenz_loader import load_gdebenz
        gdebenz = load_gdebenz(db)  # наличие из ГдеБЕНЗ (Render может спать → обновляем по кнопке)
    except Exception:
        logger.exception("gdebenz: наличие не обновлено")  # не критично
    cache_clear()  # сбросить кэш сводки — иначе /prices/summary отдаёт старое
    return {"stations": ns, "prices": npr, "cardoil": enrich, "gdebenz": gdebenz}

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

    reports = _recent_reports(db, fuel)  # {station_id: {status, at, count}}

    items: list[StationListItem] = []
    for st in stations:
        price = None
        observed = None
        available = True
        if fuel:
            # наличие = членство в fuel_types (истина card-oil там, где есть матч;
            # иначе из russiabase). Цена — из russiabase, если она есть.
            available = fuel in (st.fuel_types or [])
            match = next((p for p in st.prices if p.fuel_type == fuel), None)
            if match is not None:
                price = match.price
                observed = match.observed_at
        elif st.prices:
            dates = [p.observed_at for p in st.prices if p.observed_at]
            observed = max(dates) if dates else None
        days_old, fresh = freshness_of(observed)
        rep = reports.get(st.id)
        # свежий репорт «кончился»/«не продаётся» переопределяет каталог
        if rep and rep["status"] in ("out_of_stock", "unavailable"):
            available = False
        # Benzuber подтверждает выбранный вид (только положительно)
        bz_confirms = bool(fuel) and fuel in (st.benzuber_fuels or [])
        items.append(StationListItem(
            id=st.id, brand=st.brand, name=st.name, address=st.address,
            lat=st.lat, lon=st.lon, opening_hours=st.opening_hours,
            fuel_types=st.fuel_types, price=price,
            available=available, observed_at=observed, days_old=days_old,
            freshness=fresh,
            report_status=rep["status"] if rep else None,
            report_at=rep["at"] if rep else None,
            report_count=rep["count"] if rep else 0,
            benzuber_confirms=bz_confirms,
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
