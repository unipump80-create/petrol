"""Ручной запуск загрузки данных по Иваново.

    python scripts/load_data.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import Base, engine, SessionLocal  # noqa: E402
from app.services.russiabase_loader import load_ivanovo  # noqa: E402


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        ns, np = load_ivanovo(db)
        print(f"Загружено: {ns} станций, {np} цен")
    finally:
        db.close()


if __name__ == "__main__":
    main()
