"""Планировщик периодического обновления данных."""
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from app.database import SessionLocal
from app.services.russiabase_loader import load_ivanovo
from app.services.cardoil_loader import enrich_availability
from app.services.cache import cache_clear
from app.config import settings

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone="Europe/Moscow")


def refresh_job():
    """Обновление данных: цены из russiabase + наличие из card-oil."""
    db = SessionLocal()
    try:
        ns, npr = load_ivanovo(db)
        logger.info("refresh: %d станций, %d цен (russiabase)", ns, npr)
        # card-oil — источник истины наличия; обогащаем после загрузки цен.
        # Не валим refresh, если card-oil недоступен.
        try:
            enrich_availability(db)
        except Exception:
            logger.exception("refresh: card-oil обогащение не удалось (наличие из russiabase)")
        cache_clear()  # сводка пересчитается на следующем запросе
    except Exception:
        logger.exception("refresh: ошибка обновления данных")
    finally:
        db.close()


def start_scheduler(run_now: bool = True):
    scheduler.add_job(refresh_job, "interval", minutes=settings.refresh_minutes,
                      id="refresh", replace_existing=True)
    scheduler.start()
    if run_now:
        scheduler.add_job(refresh_job, id="refresh_now")
    logger.info("scheduler запущен (каждые %d мин)", settings.refresh_minutes)


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
