"""Основной загрузчик: АЗС + цены г. Иваново из russiabase.

Данные берутся из встроенного Next.js JSON (__NEXT_DATA__) на SSR-странице —
JS-рендеринг и Playwright не нужны. Источник бесплатный.

Структура pageProps:
  listing.listing      — записи АЗС с ценами (poiid, name, address, brand_id, ai92...)
  listing.pages        — число страниц пагинации
  listingMap.listing   — координаты (poiid -> X=lon, Y=lat)
"""
import json
import logging
import re
from datetime import datetime
import httpx
from sqlalchemy.orm import Session
from app.models import Station, Price
from app.services.fuel_codes import RUSSIABASE_MAP
from app.services.brands import normalize_brand

logger = logging.getLogger(__name__)

BASE_URL = "https://russiabase.ru/prices"
# Берём всю область и фильтруем по адресу: city=154051 узкий (теряет
# половину АЗС Иваново, которые russiabase держит на страницах области).
REGION_IVANOVO = "38"
CITY_NAME = "иваново"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
}
_NEXT_RE = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)


def _fetch_page(client: httpx.Client, page: int) -> dict:
    params = {"region": REGION_IVANOVO}
    if page > 1:
        params["page"] = page
    resp = client.get(BASE_URL, params=params)
    resp.raise_for_status()
    m = _NEXT_RE.search(resp.text)
    if not m:
        raise ValueError("__NEXT_DATA__ не найден на странице")
    return json.loads(m.group(1))["props"]["pageProps"]


def fetch_ivanovo() -> tuple[list[dict], dict]:
    """Возвращает (записи_АЗС_Иваново, карта_координат_по_poiid).

    Тянем всю область, оставляем записи с адресом в г. Иваново.
    """
    records: list[dict] = []
    coords: dict[str, dict] = {}
    with httpx.Client(timeout=60, trust_env=False, headers=HEADERS, follow_redirects=True) as c:
        first = _fetch_page(c, 1)
        pages = first["listing"].get("pages", 1)
        records.extend(first["listing"]["listing"])
        for m in first.get("listingMap", {}).get("listing", []):
            coords[m["poiid"]] = m
        for p in range(2, pages + 1):
            pp = _fetch_page(c, p)
            records.extend(pp["listing"]["listing"])
            for m in pp.get("listingMap", {}).get("listing", []):
                coords[m["poiid"]] = m
    # фильтр по городу: адрес содержит «Иваново»
    # ('Ивановская обл.' не матчит — нет окончания '-ово')
    ivanovo = [r for r in records if CITY_NAME in (r.get("address") or "").lower()]
    return ivanovo, coords


def _parse_date(value: str | None) -> datetime | None:
    """Дата наблюдения цены или None.

    None при отсутствии/нераспознаваемом формате — НЕ подставляем utcnow(),
    иначе протухшие данные выглядят как «обновлено сегодня».
    """
    if value:
        try:
            return datetime.strptime(value, "%d.%m.%Y")
        except ValueError:
            logger.warning("russiabase: не распарсил дату %r", value)
    return None


def load_ivanovo(db: Session) -> tuple[int, int]:
    """Загружает станции и цены. Возвращает (станций, цен)."""
    records, coords = fetch_ivanovo()
    n_stations = n_prices = 0
    seen_poiids = {str(r["poiid"]) for r in records}

    # удалить АЗС, которых больше нет в источнике (вместе с ценами)
    stale = db.query(Station).filter(Station.poiid.notin_(seen_poiids)).all()
    for st in stale:
        db.delete(st)

    for rec in records:
        poiid = str(rec["poiid"])
        brand = normalize_brand(rec.get("name", "").split("№")[0])
        geo = coords.get(poiid, {})

        station = db.query(Station).filter(Station.poiid == poiid).first()
        if station is None:
            station = Station(poiid=poiid)
            db.add(station)

        station.brand = brand
        station.name = rec.get("name")
        station.address = rec.get("address")
        station.source = "russiabase"
        if geo.get("Y"):
            station.lat = float(geo["Y"])
        if geo.get("X"):
            station.lon = float(geo["X"])

        observed = _parse_date(rec.get("prices_updated") or rec.get("LastUpdate"))
        available: list[str] = []

        # снести старые цены этой станции, записать актуальные
        if station.id:
            db.query(Price).filter(Price.station_id == station.id).delete()

        for field, code in RUSSIABASE_MAP.items():
            raw = rec.get(field)
            if raw in (None, "", "0"):
                continue
            try:
                price = float(str(raw).replace(",", "."))
            except ValueError:
                continue
            if price <= 0:
                continue
            db.add(Price(station=station, fuel_type=code, price=price,
                         observed_at=observed, source="russiabase"))
            available.append(code)
            n_prices += 1

        station.fuel_types = sorted(set(available))
        n_stations += 1

    db.commit()
    logger.info("russiabase: %d станций, %d цен", n_stations, n_prices)
    return n_stations, n_prices
