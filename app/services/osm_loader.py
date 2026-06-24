"""Загрузчик АЗС из OpenStreetMap через Overpass API.

Геослой: координаты, бренд, виды топлива, часы работы.
Источник бесплатный (ODbL).
"""
import logging
import httpx
from sqlalchemy.orm import Session
from app.models import Station
from app.services.fuel_codes import osm_fuels_from_tags
from app.services.brands import normalize_brand

logger = logging.getLogger(__name__)

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# bbox Иваново: (юг, запад, север, восток)
IVANOVO_BBOX = (56.95, 40.85, 57.07, 41.10)

OVERPASS_QUERY = (
    "[out:json][timeout:25];"
    'node["amenity"="fuel"]({south},{west},{north},{east});'
    "out;"
)


def fetch_osm_stations() -> list[dict]:
    """Запрашивает АЗС Иваново у Overpass. Возвращает elements."""
    s, w, n, e = IVANOVO_BBOX
    query = OVERPASS_QUERY.format(south=s, west=w, north=n, east=e)
    headers = {"User-Agent": "petrol-ivanovo/0.1 (fuel price monitor)"}
    with httpx.Client(timeout=60, trust_env=False, headers=headers) as client:
        resp = client.post(OVERPASS_URL, data={"data": query})
        resp.raise_for_status()
        return resp.json().get("elements", [])


def load_stations(db: Session) -> int:
    """Загружает/обновляет станции в БД. Возвращает число обработанных."""
    elements = fetch_osm_stations()
    count = 0
    for el in elements:
        if el.get("type") != "node":
            continue
        tags = el.get("tags", {})
        osm_id = el["id"]
        brand = normalize_brand(tags.get("brand") or tags.get("operator"))
        name = tags.get("name") or brand or "АЗС"
        fuels = osm_fuels_from_tags(tags)

        station = db.query(Station).filter(Station.osm_id == osm_id).first()
        if station is None:
            station = Station(osm_id=osm_id)
            db.add(station)

        station.brand = brand
        station.name = name
        station.lat = el.get("lat")
        station.lon = el.get("lon")
        station.opening_hours = tags.get("opening_hours")
        station.fuel_types = fuels
        station.source = "osm"
        count += 1

    db.commit()
    logger.info("OSM: загружено/обновлено %d станций", count)
    return count
