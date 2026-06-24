#!/usr/bin/env python
"""Проверить какие бренды в БД."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal, Base, engine
from app.models import Station
from sqlalchemy import func

# Инициализируем БД
Base.metadata.create_all(bind=engine)

db = SessionLocal()
try:
    # Загружаем данные
    from app.services.russiabase_loader import load_ivanovo
    print("Загружаю данные...")
    load_ivanovo(db)

    # Показываем уникальные бренды
    brands = db.query(
        Station.brand,
        func.count(Station.id).label("count")
    ).group_by(Station.brand).order_by(
        func.count(Station.id).desc()
    ).all()

    print(f"\nУникальные бренды ({len(brands)} всего):")
    for brand, count in brands:
        print(f"  {brand}: {count} станций")

finally:
    db.close()
