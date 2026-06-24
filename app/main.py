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


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    start_scheduler(run_now=False)
    yield
    stop_scheduler()


app = FastAPI(title="Petrol", version=APP_VERSION, debug=settings.debug, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
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
