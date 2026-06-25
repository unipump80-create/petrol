from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, JSON, ForeignKey, Index,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from app.database import Base
from app.utils import utcnow


class Station(Base):
    __tablename__ = "stations"

    id = Column(Integer, primary_key=True, index=True)
    poiid = Column(String, unique=True, index=True)  # id russiabase
    osm_id = Column(Integer, unique=True, index=True, nullable=True)  # обогащение OSM
    brand = Column(String, index=True)
    name = Column(String)
    address = Column(String, nullable=True)
    lat = Column(Float)
    lon = Column(Float)
    opening_hours = Column(String, nullable=True)  # из OSM
    fuel_types = Column(JSON)  # коды доступного топлива ["ai92","ai95","diesel"]
    source = Column(String, default="russiabase")
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    prices = relationship("Price", back_populates="station", cascade="all, delete-orphan")

    __table_args__ = (Index("ix_stations_brand_lat_lon", "brand", "lat", "lon"),)


class FuelType(Base):
    __tablename__ = "fuel_types"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True)  # "ai92", "ai95", "diesel"
    name = Column(String)  # "АИ-92", "АИ-95", "ДТ"


class Price(Base):
    __tablename__ = "prices"

    id = Column(Integer, primary_key=True, index=True)
    station_id = Column(Integer, ForeignKey("stations.id"), index=True)
    fuel_type = Column(String, index=True)  # код топлива
    price = Column(Float)
    # nullable: если источник дал нераспознаваемую дату — храним NULL,
    # а не фейковую «сегодня» (см. _parse_date)
    observed_at = Column(DateTime, default=utcnow, index=True, nullable=True)
    source = Column(String, default="russiabase")

    station = relationship("Station", back_populates="prices")

    __table_args__ = (
        Index("ix_prices_station_fuel", "station_id", "fuel_type"),
        # одна цена на (станция, топливо) — защита от дублей при гонке refresh
        UniqueConstraint("station_id", "fuel_type", name="uq_price_station_fuel"),
    )


class FuelReport(Base):
    """Краудсорс-репорт о наличии топлива от пользователей.

    Даёт то, чего нет ни в одном источнике-каталоге: реальный сигнал
    «кончилось прямо сейчас». Свежие репорты (за report_ttl_hours)
    переопределяют каталожное наличие в выдаче.
    """
    __tablename__ = "fuel_reports"

    id = Column(Integer, primary_key=True, index=True)
    station_id = Column(Integer, ForeignKey("stations.id"), index=True)
    fuel_type = Column(String, index=True)
    available = Column(Boolean)  # True — «есть», False — «нет»
    created_at = Column(DateTime, default=utcnow, index=True)

    __table_args__ = (
        Index("ix_reports_station_fuel_time", "station_id", "fuel_type", "created_at"),
    )
