"""Мелкие общие утилиты."""
from datetime import datetime, timezone


def utcnow() -> datetime:
    """Наивный UTC «сейчас».

    БД хранит наивные datetime; tz-aware значение сломало бы сравнения.
    Заменяет deprecated datetime.utcnow().
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)
