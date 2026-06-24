"""Кэширование результатов запросов."""
import json
from datetime import datetime, timedelta
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)

class Cache:
    """Простой in-memory кэш с TTL."""

    def __init__(self):
        self.data = {}
        self.expiry = {}

    def set(self, key: str, value: Any, ttl_seconds: int = 300):
        """Сохранить в кэш с TTL."""
        self.data[key] = value
        self.expiry[key] = datetime.utcnow() + timedelta(seconds=ttl_seconds)
        logger.debug(f"cache: set {key} (ttl={ttl_seconds}s)")

    def get(self, key: str) -> Optional[Any]:
        """Получить из кэша если ещё валиден."""
        if key not in self.data:
            return None

        if datetime.utcnow() > self.expiry.get(key, datetime.utcnow()):
            del self.data[key]
            del self.expiry[key]
            logger.debug(f"cache: expired {key}")
            return None

        logger.debug(f"cache: hit {key}")
        return self.data[key]

    def invalidate(self, key: str):
        """Инвалидировать ключ."""
        if key in self.data:
            del self.data[key]
            del self.expiry[key]
            logger.debug(f"cache: invalidate {key}")

    def clear(self):
        """Очистить весь кэш."""
        self.data.clear()
        self.expiry.clear()
        logger.info("cache: cleared")

    def stats(self) -> dict:
        """Статистика кэша."""
        return {
            "size": len(self.data),
            "keys": list(self.data.keys()),
        }


# Глобальный кэш
_cache = Cache()


def cache_get(key: str) -> Optional[Any]:
    """Получить из глобального кэша."""
    return _cache.get(key)


def cache_set(key: str, value: Any, ttl_seconds: int = 300):
    """Сохранить в глобальный кэш."""
    _cache.set(key, value, ttl_seconds)


def cache_invalidate(key: str):
    """Инвалидировать ключ в глобальном кэше."""
    _cache.invalidate(key)


def cache_stats() -> dict:
    """Получить статистику кэша."""
    return _cache.stats()


def cache_clear():
    """Очистить глобальный кэш."""
    _cache.clear()
