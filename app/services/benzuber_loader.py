"""Кросс-чек наличия топлива через Benzuber (app.benzuber.ru).

Третий независимый бесплатный источник (без авторизации). Endpoint найден
из веб-карты Benzuber (map4.js):

  GET /map?zoom=10&price_mode=0  -> GeoJSON всех АЗС РФ (id + координаты)
  GET /map?station_id={id}       -> HTML с брендом, адресом, списком топлива+цен

Benzuber заявляет интеграцию напрямую с кассами АЗС. Для каждой нашей станции
(матч по координатам того же бренда) сохраняем набор видов топлива по версии
Benzuber в Station.benzuber_fuels — для отметки «подтверждено N источниками»
или «расхождение источников».
"""
import logging
import re
import httpx
from sqlalchemy.orm import Session
from app.models import Station
from app.services.brands import normalize_brand
from app.services.cardoil_loader import _dist_m, IVANOVO_BBOX, MATCH_RADIUS_M

logger = logging.getLogger(__name__)

MAP_URL = "https://app.benzuber.ru/map"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
    "X-Requested-With": "XMLHttpRequest",
}

# Названия топлива Benzuber (.name в детали) -> наш код
_FUEL_MAP = {
    "DT": "diesel", "ДТ": "diesel",
    "AI-92": "ai92", "AI-95": "ai95", "AI-98": "ai98", "AI-100": "ai100",
    "AI-92+": "ai92plus", "AI-95+": "ai95plus", "AI-98+": "ai98plus",
    "DT+": "dieselplus",
    "PROPAN": "gas", "ПРОПАН": "gas", "METAN": "gas", "МЕТАН": "gas",
    "LPG": "gas", "CNG": "gas", "СУГ": "gas",
}

_BRAND_RE = re.compile(r'class="brand">([^<]*)<', re.I)
_ITEM_RE = re.compile(
    r'class="name">\s*([^<]+?)\s*</div>\s*<div class="price">\s*([0-9.,]+)',
    re.I | re.S,
)


def _map_fuel(name: str) -> str | None:
    key = name.strip().upper().replace("G-DRIVE", "AI-95+").replace(" ", "")
    # нормализуем «AI95»/«AI-95»
    key = key.replace("AI95PLUS", "AI-95+").replace("AI92PLUS", "AI-92+")
    if key in _FUEL_MAP:
        return _FUEL_MAP[key]
    # частичные
    for k, v in _FUEL_MAP.items():
        if k.replace(" ", "") == key:
            return v
    return None


def fetch_benzuber_ivanovo() -> list[dict]:
    """Станции Benzuber в bbox Иванова с видами топлива.

    Returns [{lat, lon, brand, fuels:set[str]}].
    """
    south, north, west, east = IVANOVO_BBOX
    out: list[dict] = []
    with httpx.Client(timeout=40, trust_env=False, headers=HEADERS,
                      follow_redirects=True) as c:
        fc = c.get(MAP_URL, params={"zoom": 10, "price_mode": 0}).json()
        ivanovo = [
            f for f in fc.get("features", [])
            if south < f["geometry"]["coordinates"][0] < north
            and west < f["geometry"]["coordinates"][1] < east
        ]
        logger.info("benzuber: %d АЗС в Иваново (из %d по РФ)",
                    len(ivanovo), len(fc.get("features", [])))
        for f in ivanovo:
            lat, lon = f["geometry"]["coordinates"][:2]
            try:
                html = c.get(MAP_URL, params={"station_id": f["id"]}).text
            except Exception:
                continue
            bm = _BRAND_RE.search(html)
            brand = normalize_brand(bm.group(1)) if bm else None
            fuels: set[str] = set()
            for nm, _price in _ITEM_RE.findall(html):
                code = _map_fuel(nm)
                if code:
                    fuels.add(code)
            if fuels:
                out.append({"lat": float(lat), "lon": float(lon),
                            "brand": brand, "fuels": sorted(fuels)})
    return out


def load_benzuber(db: Session, max_dist_m: float = MATCH_RADIUS_M) -> dict:
    """Проставляет Station.benzuber_fuels по совпадению координат+бренда.

    Returns статистику матча.
    """
    points = fetch_benzuber_ivanovo()
    by_brand: dict[str, list[dict]] = {}
    for p in points:
        by_brand.setdefault(p["brand"], []).append(p)

    stations = [s for s in db.query(Station).all() if s.lat and s.lon]
    matched = 0
    for st in stations:
        cands = by_brand.get(st.brand)
        if not cands:
            st.benzuber_fuels = None
            continue
        near = min(cands, key=lambda c: _dist_m(st.lat, st.lon, c["lat"], c["lon"]))
        if _dist_m(st.lat, st.lon, near["lat"], near["lon"]) <= max_dist_m:
            st.benzuber_fuels = near["fuels"]
            matched += 1
        else:
            st.benzuber_fuels = None

    db.commit()
    stats = {"benzuber_points": len(points), "stations": len(stations),
             "matched": matched}
    logger.info("benzuber: матч %d/%d станций", matched, len(stations))
    return stats
