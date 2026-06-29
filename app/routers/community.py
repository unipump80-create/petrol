"""Комьюнити-фичи в стиле ГдеБЕНЗ: комментарии водителей и веб-чат-бот.

- /comments  — список и добавление комментариев под АЗС.
- /chat      — простой rule-based бот: «где есть 95 рядом», «где нет ДТ»,
               «очереди», «сколько стоит 95» → ближайшие/подходящие АЗС.
"""
import logging
import re
from math import radians, sin, cos, asin, sqrt

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Station, StationAvail, Comment, Price
from app.services.fuel_codes import FUEL_TYPES

router = APIRouter(prefix="/community", tags=["community"])
logger = logging.getLogger(__name__)

IVANOVO = (57.0, 40.97)

STATE_LABEL = {
    "yes": "🟢 есть",
    "queue": "🟠 очередь",
    "low": "🟡 мало",
    "no": "🔴 нет",
}


def _dist_km(a_lat, a_lon, b_lat, b_lon) -> float:
    r = 6371.0
    dlat = radians(b_lat - a_lat)
    dlon = radians(b_lon - a_lon)
    h = sin(dlat / 2) ** 2 + cos(radians(a_lat)) * cos(radians(b_lat)) * sin(dlon / 2) ** 2
    return 2 * r * asin(sqrt(h))


# ---------- Комментарии ----------

class CommentOut(BaseModel):
    id: int
    station_id: int | None
    text: str
    author: str | None
    state: str | None
    source: str
    created_at: str | None


class CommentIn(BaseModel):
    station_id: int
    text: str
    author: str | None = None
    state: str | None = None  # yes | queue | low | no


@router.get("/comments", response_model=list[CommentOut])
def list_comments(
    station_id: int | None = Query(None),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
):
    """Комментарии под АЗС (или все последние, если station_id не задан)."""
    q = db.query(Comment)
    if station_id is not None:
        q = q.filter(Comment.station_id == station_id)
    rows = q.order_by(Comment.created_at.desc()).limit(limit).all()
    return [
        CommentOut(
            id=c.id, station_id=c.station_id, text=c.text, author=c.author,
            state=c.state, source=c.source,
            created_at=c.created_at.isoformat() if c.created_at else None,
        )
        for c in rows
    ]


@router.post("/comments", response_model=CommentOut)
def add_comment(body: CommentIn, db: Session = Depends(get_db)):
    """Добавить комментарий водителя под АЗС."""
    text = (body.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Пустой комментарий")
    if db.query(Station).filter(Station.id == body.station_id).first() is None:
        raise HTTPException(status_code=404, detail="АЗС не найдена")
    if body.state is not None and body.state not in STATE_LABEL:
        raise HTTPException(status_code=400, detail="Неизвестный статус")
    c = Comment(
        station_id=body.station_id, text=text[:500],
        author=(body.author or None), state=body.state, source="user",
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return CommentOut(
        id=c.id, station_id=c.station_id, text=c.text, author=c.author,
        state=c.state, source=c.source,
        created_at=c.created_at.isoformat() if c.created_at else None,
    )


# ---------- Отметка статуса (народная карта) ----------

class MarkIn(BaseModel):
    station_id: int
    state: str  # yes | queue | low | no


@router.post("/mark")
def mark_state(body: MarkIn, db: Session = Depends(get_db)):
    """Отметить статус АЗС (как у ГдеБЕНЗ): есть/очередь/мало/нет.

    Пишет StationAvail(source='user'). В выдаче побеждает самая свежая
    отметка по станции, поэтому ручная отметка перекрывает старую.
    """
    if body.state not in STATE_LABEL:
        raise HTTPException(status_code=400, detail="Неизвестный статус")
    if db.query(Station).filter(Station.id == body.station_id).first() is None:
        raise HTTPException(status_code=404, detail="АЗС не найдена")
    # одна пользовательская отметка на станцию — обновляем существующую
    av = (db.query(StationAvail)
          .filter(StationAvail.station_id == body.station_id,
                  StationAvail.source == "user").first())
    if av is None:
        av = StationAvail(station_id=body.station_id, source="user")
        db.add(av)
    av.state = body.state
    av.confirmations = (av.confirmations or 0) + 1
    from app.utils import utcnow
    av.last_at = utcnow()
    av.updated_at = utcnow()
    db.commit()
    return {"ok": True, "station_id": body.station_id, "state": body.state,
            "state_label": STATE_LABEL[body.state]}


def _latest_avail(db) -> dict[int, StationAvail]:
    """station_id → самая свежая отметка (gdebenz + user)."""
    out: dict[int, StationAvail] = {}
    for a in db.query(StationAvail).order_by(StationAvail.updated_at.asc()).all():
        out[a.station_id] = a
    return out


# ---------- Чат-бот ----------

class ChatIn(BaseModel):
    message: str
    lat: float | None = None
    lon: float | None = None


# Распознавание вида топлива из свободного текста
_FUEL_PATTERNS = [
    (r"\b(?:аи[\- ]?92|92[-й]?\b|92)", "ai92"),
    (r"\b(?:аи[\- ]?95|95[-й]?\b|95)", "ai95"),
    (r"\b(?:аи[\- ]?98|98[-й]?\b|98)", "ai98"),
    (r"\b(?:аи[\- ]?100|100[-й]?\b|сотый)", "ai100"),
    (r"\b(?:дт|дизел|солярк)", "diesel"),
    (r"\b(?:газ|пропан|метан|lpg|спбт)", "gas"),
]


def _detect_fuel(text: str) -> str | None:
    for pat, code in _FUEL_PATTERNS:
        if re.search(pat, text):
            return code
    return None


def _detect_state(text: str) -> str:
    """Какое наличие интересует. По умолчанию — 'есть' (yes)."""
    if re.search(r"\b(нет|кончил|закончил|отсутств|без)\b", text):
        return "no"
    if re.search(r"\b(очеред|пробк)\b", text):
        return "queue"
    if re.search(r"\b(мало|лимит|ограничен|остатк)\b", text):
        return "low"
    return "yes"


@router.post("/chat")
def chat(body: ChatIn, db: Session = Depends(get_db)):
    """Rule-based помощник по наличию и ценам топлива."""
    msg = (body.message or "").lower().strip()
    if not msg:
        return {"answer": "Спросите: «где есть 95 рядом» или «сколько стоит ДТ».",
                "stations": []}

    origin = (body.lat, body.lon) if (body.lat and body.lon) else IVANOVO
    fuel = _detect_fuel(msg)
    fuel_name = FUEL_TYPES.get(fuel, "топливо") if fuel else "топливо"

    price_mode = bool(re.search(r"\b(цена|цен[аыу]|стоит|стоим|сколько|дешев|дорог)\b", msg))

    stations = [s for s in db.query(Station).all() if s.lat and s.lon]
    # фильтр по виду топлива (продаётся на АЗС)
    if fuel:
        stations = [s for s in stations if fuel in (s.fuel_types or [])]

    if price_mode:
        return _answer_prices(db, stations, fuel, fuel_name, origin)

    return _answer_avail(db, stations, fuel, fuel_name, origin, _detect_state(msg))


def _answer_avail(db, stations, fuel, fuel_name, origin, state):
    avail = _latest_avail(db)
    rows = []
    for s in stations:
        a = avail.get(s.id)
        if a is None or a.state != state:
            continue
        rows.append((s, a, _dist_km(origin[0], origin[1], s.lat, s.lon)))
    rows.sort(key=lambda x: x[2])
    top = rows[:8]

    label = STATE_LABEL.get(state, state)
    if not top:
        ans = (f"Нет данных о статусе «{label}»"
               + (f" по {fuel_name}" if fuel else "") + " рядом.")
    else:
        verb = {"yes": "есть", "no": "нет", "queue": "очереди с",
                "low": "мало"}.get(state, state)
        ans = (f"{label}: {fuel_name if fuel else 'топливо'} «{verb}» — "
               f"нашёл {len(top)} АЗС, ближайшие сверху.")
    return {
        "answer": ans,
        "stations": [
            {"id": s.id, "name": s.name, "address": s.address,
             "lat": s.lat, "lon": s.lon, "state": a.state,
             "state_label": STATE_LABEL.get(a.state, a.state),
             "confirmations": a.confirmations,
             "dist_km": round(d, 1)}
            for s, a, d in top
        ],
    }


def _answer_prices(db, stations, fuel, fuel_name, origin):
    if not fuel:
        return {"answer": "Уточните вид топлива: «сколько стоит 95?»", "stations": []}
    ids = [s.id for s in stations]
    prices = {
        p.station_id: p.price
        for p in db.query(Price).filter(
            Price.fuel_type == fuel, Price.station_id.in_(ids)).all()
    }
    rows = [(s, prices[s.id], _dist_km(origin[0], origin[1], s.lat, s.lon))
            for s in stations if s.id in prices]
    if not rows:
        return {"answer": f"Нет цен по {fuel_name}.", "stations": []}
    rows.sort(key=lambda x: x[1])
    top = rows[:8]
    cheapest = top[0]
    ans = (f"Дешевле всего {fuel_name}: {cheapest[1]:.2f} ₽ "
           f"({cheapest[0].name}). Топ-{len(top)} по цене ниже.")
    return {
        "answer": ans,
        "stations": [
            {"id": s.id, "name": s.name, "address": s.address,
             "lat": s.lat, "lon": s.lon, "price": round(pr, 2),
             "dist_km": round(d, 1)}
            for s, pr, d in top
        ],
    }
