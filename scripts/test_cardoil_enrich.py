#!/usr/bin/env python
"""Тест обогащения наличия из card-oil + выдачи /stations."""
import sys, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ["DATABASE_URL"] = "sqlite:///./petrol_test_enrich.db"

from app.database import SessionLocal, Base, engine
from app.models import Station
from app.services.russiabase_loader import load_ivanovo
from app.services.cardoil_loader import enrich_availability
from fastapi.testclient import TestClient
from app.main import app

Base.metadata.create_all(bind=engine)
db = SessionLocal()

# 1. russiabase (цены + наличие из цен)
ns, npr = load_ivanovo(db)
before = {s.id: list(s.fuel_types or []) for s in db.query(Station).all()}

# 2. card-oil обогащение наличия
stats = enrich_availability(db)
print("ENRICH:", stats)

# 3. что изменилось
after = {s.id: list(s.fuel_types or []) for s in db.query(Station).all()}
added_total = 0
examples = []
for sid, fb in before.items():
    fa = after.get(sid, fb)
    if set(fa) != set(fb):
        added = sorted(set(fa) - set(fb))
        removed = sorted(set(fb) - set(fa))
        added_total += len(added)
        if len(examples) < 8:
            st = db.query(Station).get(sid)
            examples.append(f"  {st.brand} {st.name}: +{added} -{removed}")
print(f"\nизменено станций: {sum(1 for s in before if set(after.get(s,before[s]))!=set(before[s]))}")
print(f"добавлено видов топлива всего: {added_total}")
for e in examples: print(e)

db.close()

# 4. API выдача с наличием
client = TestClient(app)
r = client.get("/stations?fuel=ai98&sort=price")
data = r.json()
avail = [s for s in data if s["available"]]
print(f"\n/stations?fuel=ai98: всего {len(data)}, с наличием ai98: {len(avail)}")
withprice = [s for s in avail if s["price"] is not None]
print(f"  из них с ценой: {len(withprice)}, без цены (наличие есть, цены нет): {len(avail)-len(withprice)}")

os.remove("./petrol_test_enrich.db") if os.path.exists("./petrol_test_enrich.db") else None
