"""Загрузчик наличия топлива с card-oil.ru.

Источник: статический JSON карты card-oil, который использует их веб-виджет
(https://map.card-oil.ru). JS/Playwright НЕ нужны.

  https://cdn2.card-oil.ru/map/FilterAZS.json   (~1.9 МБ, вся РФ)

Структура — колоночная: {"headers": [...23 поля...], "data": [[...], ...]}.
Поля топлива (DT, Ai92, Ai95, Ai98, Ai100, Gaz, Metan) — ФЛАГИ наличия 1/0.
ЦЕН В ИСТОЧНИКЕ НЕТ — только наличие видов топлива, бренд, координаты.

Поэтому card-oil даёт более точное «наличие», а цены берутся из russiabase.
"""
import logging
import httpx
from sqlalchemy.orm import Session
from app.models import Station
from app.services.brands import normalize_brand

logger = logging.getLogger(__name__)

POINTS_URL = "https://cdn2.card-oil.ru/map/FilterAZS.json"

# bbox Иваново (юг, север, запад, восток)
IVANOVO_BBOX = (56.90, 57.15, 40.70, 41.25)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
}

import math

# Имя колонки в FilterAZS.json -> наш код топлива (см. app/services/fuel_codes).
# Несколько колонок могут мапиться в один код (Gaz/Metan -> gas).
FUEL_COLUMNS = {
    "DT": "diesel",
    "DTP": "dieselplus",
    "Ai92": "ai92",
    "Ai92P": "ai92plus",
    "Ai95": "ai95",
    "Ai95P": "ai95plus",
    "Ai98": "ai98",
    "Ai100": "ai100",
    "Gaz": "gas",
    "Metan": "gas",
}

# Радиус уверенного сопоставления russiabase<->card-oil (метры)
MATCH_RADIUS_M = 150


def _dist_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Грубое расстояние в метрах (плоская аппроксимация, хватает для <1 км)."""
    dlat = (lat1 - lat2) * 111_000
    dlon = (lon1 - lon2) * 111_000 * math.cos(math.radians(lat1))
    return math.hypot(dlat, dlon)


def fetch_cardoil_points(bbox: tuple[float, float, float, float] = IVANOVO_BBOX) -> list[dict]:
    """Скачивает FilterAZS.json и возвращает АЗС внутри bbox.

    Returns:
        Список dict: {poiid, brand, lat, lon, fuel_types}.
        fuel_types — отсортированный список кодов топлива с флагом наличия=1.
    """
    south, north, west, east = bbox
    with httpx.Client(timeout=60, trust_env=False, headers=HEADERS,
                      follow_redirects=True) as client:
        resp = client.get(POINTS_URL)
        resp.raise_for_status()
        payload = resp.json()

    headers = payload["headers"]
    idx = {name: i for i, name in enumerate(headers)}
    i_id, i_brand = idx["ID"], idx["Brand"]
    i_lat, i_lon = idx["latitude"], idx["longitude"]

    stations: list[dict] = []
    for row in payload["data"]:
        try:
            lat = float(row[i_lat]); lon = float(row[i_lon])
        except (TypeError, ValueError):
            continue
        if not (south < lat < north and west < lon < east):
            continue

        # собрать доступные виды топлива по флагам 1/0
        fuels: set[str] = set()
        for col, code in FUEL_COLUMNS.items():
            if col in idx and row[idx[col]] == 1:
                fuels.add(code)
        if not fuels:
            continue

        stations.append({
            "poiid": f"cardoil_{row[i_id]}",
            "brand": normalize_brand(str(row[i_brand])),
            "lat": lat,
            "lon": lon,
            "fuel_types": sorted(fuels),
        })

    logger.info("cardoil: %d АЗС в bbox (из %d по РФ)",
                len(stations), len(payload["data"]))
    return stations


def load_cardoil_ivanovo(db: Session) -> tuple[int, int]:
    """Загружает наличие топлива по АЗС Иванова из card-oil.

    Возвращает (станций, 0) — цен у источника нет, второй элемент всегда 0
    для совместимости с сигнатурой russiabase-загрузчика.
    """
    points = fetch_cardoil_points()
    n = 0
    seen = {p["poiid"] for p in points}

    # снести станции card-oil, которых больше нет в источнике
    stale = (
        db.query(Station)
        .filter(Station.poiid.like("cardoil_%"))
        .filter(Station.poiid.notin_(seen))
        .all()
    )
    for st in stale:
        db.delete(st)

    for p in points:
        station = db.query(Station).filter(Station.poiid == p["poiid"]).first()
        if station is None:
            station = Station(poiid=p["poiid"])
            db.add(station)
        station.brand = p["brand"]
        station.name = p["brand"]  # источник не даёт отдельного имени/№
        station.lat = p["lat"]
        station.lon = p["lon"]
        station.fuel_types = p["fuel_types"]
        station.source = "cardoil"
        n += 1

    db.commit()
    logger.info("cardoil: загружено/обновлено %d станций (без цен)", n)
    return n, 0


def enrich_availability(db: Session, bbox: tuple = IVANOVO_BBOX,
                        max_dist_m: float = MATCH_RADIUS_M) -> dict:
    """Обновляет наличие топлива (fuel_types) станций russiabase по card-oil.

    Card-oil — источник истины наличия: для каждой станции russiabase ищем
    ближайшую точку card-oil ТОГО ЖЕ бренда в радиусе max_dist_m и берём её
    набор видов топлива как авторитетный (перезаписываем fuel_types).

    Цены не трогаем — они остаются из russiabase. Станции без совпадения
    остаются как есть (наличие из russiabase).

    Returns:
        Статистика обогащения.
    """
    points = fetch_cardoil_points(bbox)
    by_brand: dict[str, list[dict]] = {}
    for p in points:
        by_brand.setdefault(p["brand"], []).append(p)

    # только станции russiabase (не сами cardoil_*)
    rb_stations = [
        s for s in db.query(Station).all()
        if s.lat and s.lon and not (s.poiid or "").startswith("cardoil_")
    ]

    matched = changed = 0
    for st in rb_stations:
        candidates = by_brand.get(st.brand)
        if not candidates:
            continue
        near = min(candidates, key=lambda c: _dist_m(st.lat, st.lon, c["lat"], c["lon"]))
        if _dist_m(st.lat, st.lon, near["lat"], near["lon"]) > max_dist_m:
            continue
        matched += 1
        new_fuels = near["fuel_types"]
        if new_fuels and new_fuels != (st.fuel_types or []):
            st.fuel_types = new_fuels
            changed += 1

    db.commit()
    stats = {
        "cardoil_points": len(points),
        "russiabase_stations": len(rb_stations),
        "matched": matched,
        "availability_updated": changed,
    }
    logger.info("cardoil enrich: матч %d/%d, обновлено наличие у %d",
                matched, len(rb_stations), changed)
    return stats
