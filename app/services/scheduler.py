"""Планировщик периодического обновления данных."""
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from app.database import SessionLocal
from app.services.russiabase_loader import load_ivanovo
from app.services.cardoil_loader import load_cardoil_ivanovo
from app.config import settings

logger = logging.getLogger(__name__)

# Цены меняются редко — обновляем раз в 6 часов.
REFRESH_HOURS = 6

scheduler = BackgroundScheduler(timezone="Europe/Moscow")


def refresh_job():
    """Обновление данных из выбранного источника."""
    db = SessionLocal()
    try:
        if settings.data_source == "cardoil":
            ns, np = load_cardoil_ivanovo(db)
        else:
            ns, np = load_ivanovo(db)
        logger.info("refresh: %d станций, %d цен (включая Газпромнефть)", ns, np)
    except Exception:
        logger.exception("refresh: ошибка обновления данных")
    finally:
        db.close()


def start_scheduler(run_now: bool = True):
    scheduler.add_job(refresh_job, "interval", hours=REFRESH_HOURS,
                      id="refresh", replace_existing=True)
    scheduler.start()
    if run_now:
        scheduler.add_job(refresh_job, id="refresh_now")
    logger.info("scheduler запущен (каждые %d ч)", REFRESH_HOURS)


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
