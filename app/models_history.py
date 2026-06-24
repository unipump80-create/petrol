from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, String
from app.database import Base
from app.utils import utcnow

class PriceHistory(Base):
    __tablename__ = "price_history"
    
    id = Column(Integer, primary_key=True, index=True)
    station_id = Column(Integer, ForeignKey("stations.id"), index=True)
    fuel_type = Column(String, index=True)
    price = Column(Float)
    recorded_at = Column(DateTime, default=utcnow, index=True)
    source = Column(String)
