#!/usr/bin/env python
"""Debug поиска Газпромнефти."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal, Base, engine
from app.models import Station

Base.metadata.create_all(bind=engine)
db = SessionLocal()

print("Загружаю данные...")
from app.services.russiabase_loader import load_ivanovo
load_ivanovo(db)

print("\nТест фильтра ilike:")
gazprom_ilike = db.query(Station).filter(Station.brand.ilike("%газпром%")).all()
print(f"  Результат: {len(gazprom_ilike)}")

print("\nТест фильтра with_entities (все бренды):")
all_stations = db.query(Station).all()
gazprom_manual = [s for s in all_stations if "газпром" in (s.brand or "").lower()]
print(f"  Результат: {len(gazprom_manual)}")

print("\nИмена станций Газпромнефти:")
for st in gazprom_manual[:5]:
    print(f"  Brand: '{st.brand}'")
    print(f"    Name: {st.name}")
    print(f"    Fuel types: {st.fuel_types}")
    print(f"    Prices: {[(p.fuel_type, p.price) for p in st.prices]}")
    print()
