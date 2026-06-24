from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./petrol.db"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    # CORS: список доменов через запятую. PWA ходит в свой же origin,
    # кросс-доменный доступ по умолчанию не нужен. "*" — только для отладки.
    cors_origins: str = "*"
    # минимальный интервал между обновлениями из источника (сек)
    refresh_min_interval: int = 300

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
