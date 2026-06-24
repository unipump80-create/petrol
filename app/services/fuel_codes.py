"""Единые коды топлива и маппинг из разных источников.

Внутренний код — единая точка связи OSM (geo) и fuelprice (цены).
"""

# Внутренний код -> человекочитаемое имя
FUEL_TYPES = {
    "ai92": "АИ-92",
    "ai95": "АИ-95",
    "ai98": "АИ-98",
    "ai100": "АИ-100",
    "diesel": "ДТ",
    "gas": "Газ",
    "ai92plus": "АИ-92+",
    "ai95plus": "АИ-95+",
    "ai98plus": "АИ-98+",
    "dieselplus": "ДТ+",
}

# Теги OSM (fuel:*) -> внутренний код
OSM_FUEL_MAP = {
    "octane_92": "ai92",
    "octane_95": "ai95",
    "octane_98": "ai98",
    "octane_100": "ai100",
    "diesel": "diesel",
    "lpg": "gas",
    "cng": "gas",
}

# Поля russiabase __NEXT_DATA__ -> внутренний код.
# Премиум-варианты (ai95plus и т.п.) храним отдельными кодами.
RUSSIABASE_MAP = {
    "ai92": "ai92",
    "ai95": "ai95",
    "ai98": "ai98",
    "ai100": "ai100",
    "dt": "diesel",
    "gas": "gas",
    "propan": "gas",
    "ai92plus": "ai92plus",
    "ai95plus": "ai95plus",
    "ai98plus": "ai98plus",
    "dtplus": "dieselplus",
}

def osm_fuels_from_tags(tags: dict) -> list[str]:
    """Извлекает внутренние коды топлива из тегов OSM-ноды."""
    codes = set()
    for key, value in tags.items():
        if not key.startswith("fuel:"):
            continue
        if str(value).lower() not in ("yes", "true", "1"):
            continue
        osm_key = key[len("fuel:"):]
        code = OSM_FUEL_MAP.get(osm_key)
        if code:
            codes.add(code)
    return sorted(codes)
