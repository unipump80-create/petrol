from datetime import datetime
from pydantic import BaseModel, ConfigDict


class PriceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    fuel_type: str
    fuel_name: str
    price: float
    observed_at: datetime | None


class StationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    brand: str | None
    name: str | None
    address: str | None
    lat: float | None
    lon: float | None
    opening_hours: str | None
    fuel_types: list[str] | None
    prices: list[PriceOut]


class StationListItem(BaseModel):
    """Лёгкий вид для списка/карты: одна цена по выбранному топливу."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    brand: str | None
    name: str | None
    address: str | None
    lat: float | None
    lon: float | None
    opening_hours: str | None = None  # часы работы из OSM (часто "24/7")
    fuel_types: list[str] | None
    price: float | None  # цена по запрошенному виду топлива (если задан fuel)
    available: bool  # продаётся ли выбранный вид топлива на этой АЗС
    observed_at: datetime | None  # когда цена обновлена в источнике
    days_old: int | None  # сколько дней назад
    freshness: str | None  # fresh | recent | stale
    # краудсорс-наличие (свежие репорты пользователей по выбранному топливу)
    report_status: str | None = None  # "out" — сообщают «нет»; "ok" — «есть»; None — нет репортов
    report_at: datetime | None = None  # время последнего репорта
    report_count: int = 0  # сколько репортов за окно актуальности
    # независимое подтверждение наличия Benzuber (только положительное:
    # молчание Benzuber ≠ отсутствие, он часто недорепортит)
    benzuber_confirms: bool = False


class ReportIn(BaseModel):
    """Тело запроса репорта о наличии."""
    fuel_type: str
    available: bool


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
