from datetime import datetime
from pydantic import BaseModel


class PriceOut(BaseModel):
    fuel_type: str
    fuel_name: str
    price: float
    observed_at: datetime

    class Config:
        from_attributes = True


class StationOut(BaseModel):
    id: int
    brand: str | None
    name: str | None
    address: str | None
    lat: float | None
    lon: float | None
    opening_hours: str | None
    fuel_types: list[str] | None
    prices: list[PriceOut]

    class Config:
        from_attributes = True


class StationListItem(BaseModel):
    """Лёгкий вид для списка/карты: одна цена по выбранному топливу."""
    id: int
    brand: str | None
    name: str | None
    address: str | None
    lat: float | None
    lon: float | None
    fuel_types: list[str] | None
    price: float | None  # цена по запрошенному виду топлива (если задан fuel)
    available: bool  # продаётся ли выбранный вид топлива на этой АЗС
    observed_at: datetime | None  # когда цена обновлена в источнике
    days_old: int | None  # сколько дней назад
    freshness: str | None  # fresh | recent | stale

    class Config:
        from_attributes = True


class FuelSummary(BaseModel):
    fuel_type: str
    fuel_name: str
    count: int
    min: float
    avg: float
    max: float


class PricesSummary(BaseModel):
    city: str
    stations: int
    fuels: list[FuelSummary]
    updated_at: datetime | None
