import logging
import time

from app.core.config import settings
from app.db.base import SessionLocal
from app.services.reminders import run_reminder_cycle

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("caremeds.worker")


def main() -> None:
    if SessionLocal is None:
        raise RuntimeError("Database not configured. Set DATABASE_URL before starting the worker.")
    logger.info("CareMeds reminder worker started; polling every %s seconds", settings.WORKER_POLL_SECONDS)
    while True:
        db = SessionLocal()
        try:
            result = run_reminder_cycle(db)
            logger.info("Reminder cycle complete: %s", result)
        except Exception:
            logger.exception("Reminder cycle failed")
            db.rollback()
        finally:
            db.close()
        time.sleep(settings.WORKER_POLL_SECONDS)


if __name__ == "__main__":
    main()
