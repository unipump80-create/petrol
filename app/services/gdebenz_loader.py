"""
Лоадер ГдеБЕНЗ (gdebenz.ru) — краудсорсинговое наличие топлива на АЗС.

Бесплатный JSON-API без авторизации:
    GET https://gdebenz.ru/api/nearby?lat=&lon=
    -> {"summary": {...}, "stations": [{"osm_id","status","confirmed",
                                        "confirmations","last_at",...}]}
    status: yes | queue | low | no

Берём НЕГАТИВНЫЙ сигнал ("no" = нет топлива) и пишем FuelReport(out_of_stock)
по топливам станции (джойн по osm_id). Позитив ("yes/low/queue") оставляем
ценовому каталогу/Benzuber — станция-уровневый "yes" не означает наличие
каждого вида топлива.
"""
import logging
import ssl
import time
from datetime import datetime

import httpx
from sqlalchemy.orm import Session

from app.models import Station, FuelReport, StationAvail, Comment
from app.services.cardoil_loader import _dist_m, MATCH_RADIUS_M

logger = logging.getLogger(__name__)

NEARBY_URL = "https://gdebenz.ru/api/nearby"
COMMENTS_URL = "https://gdebenz.ru/api/comments"
IVANOVO = (57.0, 40.97)  # центр для api/nearby
HEADERS = {"User-Agent": "Mozilla/5.0"}
SOURCE = "gdebenz"

# Маппинг статусов ГдеБЕНЗ → наш статус наличия
#   no                  → out_of_stock (нет топлива)
#   yes / low / queue   → in_stock     (топливо есть; low=мало, queue=очередь)
_STATUS_MAP = {
    "no": "out_of_stock",
    "yes": "in_stock",
    "low": "in_stock",
    "queue": "in_stock",
}
# Если у станции не заданы виды топлива — помечаем базовый набор
_CORE_FUELS = ["ai92", "ai95", "ai98", "diesel"]


def _parse_dt(val) -> datetime | None:
    """Парсит '2026-06-26 06:06:00' / ISO → datetime, иначе None."""
    if not val:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(str(val)[:19], fmt)
        except ValueError:
            continue
    return None


def _ssl_context() -> ssl.SSLContext:
    """SSL-контекст с пониженным уровнем безопасности и широким набором шифров.

    С дата-центров (Render) gdebenz.ru обрывает TLS-рукопожатие
    (SSL: UNEXPECTED_EOF_WHILE_READING) при дефолтном наборе шифров.
    SECLEVEL=1 + DEFAULT восстанавливает совместимость.
    """
    ctx = ssl.create_default_context()
    try:
        ctx.set_ciphers("DEFAULT@SECLEVEL=1")
    except ssl.SSLError:
        pass
    return ctx


def _fetch_curl_cffi(lat: float, lon: float) -> dict | None:
    """Запрос с имитацией TLS-фингерпринта Chrome (обход WAF gdebenz.ru).

    gdebenz.ru с дата-центров (Render) рвёт рукопожатие для не-браузерных
    клиентов (SSL EOF). curl_cffi impersonate=chrome повторяет JA3 браузера.
    Возвращает None, если библиотека недоступна.
    """
    try:
        from curl_cffi import requests as cffi
    except Exception:
        return None
    # WAF gdebenz.ru нестабильно пропускает с дата-центров — пробуем несколько
    # профилей браузера (разные JA3). Таймаут короткий, чтобы /refresh не висел.
    last = None
    for imp in ("chrome", "safari", "edge99"):
        try:
            r = cffi.get(NEARBY_URL, params={"lat": lat, "lon": lon},
                         impersonate=imp, timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            last = e
    if last:
        raise last
    return None


def _fetch_nearby(lat: float, lon: float, attempts: int = 2) -> dict:
    """GET api/nearby. curl_cffi (профили браузера), фоллбэк httpx.
    Время ограничено, чтобы /refresh не зависал при блокировке WAF."""
    last: Exception = RuntimeError("no attempts")
    for i in range(attempts):
        try:
            data = _fetch_curl_cffi(lat, lon)
            if data is not None:
                return data
        except Exception as e:
            last = e
        try:  # фоллбэк httpx
            with httpx.Client(timeout=10, trust_env=False, headers=HEADERS,
                              verify=_ssl_context(), http2=False) as c:
                return c.get(NEARBY_URL, params={"lat": lat, "lon": lon}).json()
        except Exception as e:
            last = e
        if i < attempts - 1:
            time.sleep(2)
    raise last


def load_gdebenz(db: Session, center: tuple[float, float] = IVANOVO) -> dict:
    """Тянет наличие из ГдеБЕНЗ и обновляет FuelReport(source='gdebenz').

    Возвращает {"checked", "no_fuel", "reports"}.
    """
    lat, lon = center
    data = _fetch_nearby(lat, lon)

    stations = data.get("stations", []) or []

    # Защита от транзиентного пустого ответа: не стираем прошлые отчёты,
    # если источник ничего не вернул (иначе наличие «пропадёт» на ровном месте).
    if not stations:
        logger.warning("gdebenz: пустой ответ — отчёты сохранены, обновление пропущено")
        return {"checked": 0, "no_fuel": 0, "reports": 0}

    # Наши станции имеют координаты, но не osm_id — сопоставляем по близости
    # (как benzuber/cardoil), а не по osm_id.
    ours = [s for s in db.query(Station).all() if s.lat and s.lon]

    # Сносим прошлые отчёты ГдеБЕНЗ — держим только актуальное состояние
    db.query(FuelReport).filter(FuelReport.source == SOURCE).delete(
        synchronize_session=False
    )
    db.query(StationAvail).filter(StationAvail.source == SOURCE).delete(
        synchronize_session=False
    )

    no_fuel = 0
    has_fuel = 0
    reports = 0
    used: set[int] = set()
    for item in stations:
        if not item.get("confirmed"):
            continue  # только подтверждённые отметки
        our_status = _STATUS_MAP.get(item.get("status"))
        if our_status is None:
            continue
        lat, lon = item.get("lat"), item.get("lon")
        if lat is None or lon is None:
            continue

        # ближайшая наша станция в радиусе MATCH_RADIUS_M
        best, best_d = None, MATCH_RADIUS_M
        for st in ours:
            if st.id in used:
                continue
            d = _dist_m(lat, lon, st.lat, st.lon)
            if d < best_d:
                best, best_d = st, d
        if best is None:
            continue
        used.add(best.id)

        if our_status == "out_of_stock":
            no_fuel += 1
        else:
            has_fuel += 1
        fuels = best.fuel_types or _CORE_FUELS
        for f in fuels:
            db.add(FuelReport(
                station_id=best.id, fuel_type=f,
                status=our_status, source=SOURCE,
            ))
            reports += 1

        # Станционный 4-state статус (native ГдеБЕНЗ) для пина на карте
        db.add(StationAvail(
            station_id=best.id,
            state=item.get("status"),                  # yes | queue | low | no
            confirmations=item.get("confirmations") or 0,
            last_at=_parse_dt(item.get("last_at")),
            source=SOURCE,
        ))

    db.commit()
    logger.info("gdebenz: %d без топлива, %d с топливом, %d отчётов (из %d отметок)",
                no_fuel, has_fuel, reports, len(stations))
    return {"checked": len(stations), "no_fuel": no_fuel,
            "has_fuel": has_fuel, "reports": reports}


# Bbox Иваново для /api/comments (lat1,lon1 — ЮЗ; lat2,lon2 — СВ)
IVANOVO_BBOX = (56.9, 40.8, 57.1, 41.2)


def _fetch_comments(bbox: tuple[float, float, float, float]) -> list[dict]:
    """GET /api/comments по bbox. curl_cffi → httpx, как и nearby."""
    lat1, lon1, lat2, lon2 = bbox
    params = {"lat1": lat1, "lon1": lon1, "lat2": lat2, "lon2": lon2}
    try:
        from curl_cffi import requests as cffi
        for imp in ("chrome", "safari"):
            try:
                r = cffi.get(COMMENTS_URL, params=params, impersonate=imp, timeout=10)
                r.raise_for_status()
                return r.json() or []
            except Exception:
                continue
    except Exception:
        pass
    with httpx.Client(timeout=10, trust_env=False, headers=HEADERS,
                      verify=_ssl_context(), http2=False) as c:
        return c.get(COMMENTS_URL, params=params).json() or []


def load_gdebenz_comments(db: Session, bbox=IVANOVO_BBOX) -> dict:
    """Тянет комментарии водителей из ГдеБЕНЗ и сохраняет (source='gdebenz').

    Привязка к нашей станции — по близости (как наличие). Дедуп по ext_id.
    Возвращает {"fetched", "saved"}.
    """
    raw = _fetch_comments(bbox)
    # API может вернуть список или {"comments":[...]}
    items = raw.get("comments", []) if isinstance(raw, dict) else raw
    if not items:
        return {"fetched": 0, "saved": 0}

    ours = [s for s in db.query(Station).all() if s.lat and s.lon]
    existing = {
        c.ext_id for c in db.query(Comment).filter(
            Comment.source == SOURCE, Comment.ext_id.isnot(None)).all()
    }
    saved = 0
    for it in items:
        ext = str(it.get("id")) if it.get("id") is not None else None
        if ext and ext in existing:
            continue
        text = (it.get("text") or it.get("comment") or "").strip()
        if not text:
            continue
        lat, lon = it.get("lat"), it.get("lon")
        st_id = None
        if lat is not None and lon is not None:
            best, best_d = None, MATCH_RADIUS_M
            for st in ours:
                d = _dist_m(lat, lon, st.lat, st.lon)
                if d < best_d:
                    best, best_d = st, d
            st_id = best.id if best else None
        c = Comment(
            station_id=st_id, text=text[:500],
            author=(it.get("author") or it.get("name") or None),
            state=it.get("status"), source=SOURCE, ext_id=ext,
        )
        dt = _parse_dt(it.get("created_at") or it.get("last_at"))
        if dt is not None:
            c.created_at = dt
        db.add(c)
        saved += 1
        if ext:
            existing.add(ext)
    db.commit()
    logger.info("gdebenz: комментарии %d получено, %d сохранено", len(items), saved)
    return {"fetched": len(items), "saved": saved}
