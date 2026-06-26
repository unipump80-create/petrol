from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from app.database import Base, engine
from app.config import settings
from app.services.scheduler import start_scheduler, stop_scheduler
from app.routers import stations, prices

import os


def _resolve_version() -> str:
    """Версия = короткий git-хеш деплоя. На Render — из RENDER_GIT_COMMIT,
    локально — из git. Так каждый деплой автоматически даёт новую версию,
    SW обновляется и у пользователей всплывает баннер — без ручного бампа."""
    commit = os.getenv("RENDER_GIT_COMMIT")
    if not commit:
        try:
            import subprocess
            commit = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True, text=True, timeout=2,
                cwd=Path(__file__).resolve().parent.parent,
            ).stdout.strip()
        except Exception:
            commit = ""
    return f"0.2.0+{commit[:7]}" if commit else "0.2.0"


APP_VERSION = _resolve_version()


def _auto_migrate() -> None:
    """Лёгкая авто-миграция SQLite без Alembic — защита от 500 при дрейфе
    схемы на персистентной БД (create_all не добавляет колонки/не меняет тип):

    1. fuel_reports со старой колонкой 'available' (вместо 'status') —
       пересоздаём (репорты эфемерны, TTL часы, потеря безопасна).
    2. stations: ADD COLUMN для любых колонок модели, которых нет в таблице
       (напр. benzuber_fuels, добавленный позже).
    """
    from sqlalchemy import inspect, text
    from app.models import Station, FuelReport

    insp = inspect(engine)
    tables = insp.get_table_names()

    if "fuel_reports" in tables:
        cols = {c["name"] for c in insp.get_columns("fuel_reports")}
        if "status" not in cols:
            with engine.begin() as conn:
                conn.execute(text("DROP TABLE fuel_reports"))
            insp = inspect(engine)
            tables = insp.get_table_names()
        else:
            # ADD COLUMN для новых полей модели (напр. source)
            for col in FuelReport.__table__.columns:
                if col.name not in cols:
                    sqltype = col.type.compile(engine.dialect)
                    with engine.begin() as conn:
                        conn.execute(text(
                            f'ALTER TABLE fuel_reports ADD COLUMN "{col.name}" {sqltype}'))

    if "stations" in tables:
        existing = {c["name"] for c in insp.get_columns("stations")}
        for col in Station.__table__.columns:
            if col.name not in existing:
                sqltype = col.type.compile(engine.dialect)
                with engine.begin() as conn:
                    conn.execute(text(
                        f'ALTER TABLE stations ADD COLUMN "{col.name}" {sqltype}'))


@asynccontextmanager
async def lifespan(app: FastAPI):
    _auto_migrate()
    Base.metadata.create_all(bind=engine)
    _ensure_data()
    start_scheduler(run_now=False)
    yield
    stop_scheduler()


def _ensure_data() -> None:
    """Грузим данные при старте, если БД пуста.

    На Render /tmp — tmpfs: запечённая на билде БД на рантайме недоступна,
    поэтому полагаться на build-time load_data.py нельзя. Самозаполнение тут
    гарантирует данные на любом холодном старте.
    """
    import logging
    from app.database import SessionLocal
    from app.models import Station
    from app.services.russiabase_loader import load_ivanovo
    from app.services.cardoil_loader import enrich_availability

    log = logging.getLogger(__name__)
    db = SessionLocal()
    try:
        if db.query(Station).count() > 0:
            return
        log.info("БД пуста — загружаю данные из источника…")
        ns, npr = load_ivanovo(db)
        log.info("Стартовая загрузка: %d станций, %d цен", ns, npr)
        # card-oil — источник истины наличия; обогащаем сразу при старте,
        # иначе на free-тарифе (частые холодные старты) обогащение из
        # планировщика (раз в 6 ч) фактически не успевает отработать.
        try:
            st = enrich_availability(db)
            log.info("Стартовое обогащение card-oil: %s", st)
        except Exception:
            log.exception("Стартовое обогащение card-oil не удалось (наличие из russiabase)")
    except Exception:
        log.exception("Стартовая загрузка не удалась — пустая БД")
    finally:
        db.close()


app = FastAPI(title="Petrol", version=APP_VERSION, debug=settings.debug, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    # credentials не используем (нет кук/сессий) — и с wildcard это невалидно
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(stations.router)
app.include_router(prices.router)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/version")
def version():
    return {"version": APP_VERSION}


@app.get("/")
def root():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/manifest.webmanifest")
def manifest():
    return FileResponse(STATIC_DIR / "manifest.webmanifest",
                        media_type="application/manifest+json")


@app.get("/sw.js")
def service_worker():
    # отдаём из корня — иначе scope не покроет всё приложение.
    # no-cache обязателен: иначе браузер не заметит новую версию SW.
    # Версию кэша подставляем из APP_VERSION (git-хеш деплоя): тело SW
    # меняется при каждом деплое -> браузер видит обновление автоматически,
    # руками править sw.js не нужно.
    body = (STATIC_DIR / "sw.js").read_text(encoding="utf-8")
    body = body.replace("__VERSION__", APP_VERSION)
    return Response(
        content=body,
        media_type="application/javascript",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)
