# Тестирование и исправление багов Petrol

## Локальное тестирование

```bash
# Установка зависимостей
pip install -r requirements.txt pytest pytest-asyncio

# Запуск тестов
pytest -v

# Линтинг
pylint app/ --disable=all --enable=E
```

## Автоматическое тестирование

Все коммиты в `master` и `main` автоматически:
1. Запускают тесты (GitHub Actions)
2. Проверяют синтаксис Python
3. Логируют результаты в Actions tab

## Типичные баги и исправление

### Карта не загружается
- Проверь интернет соединение
- Очисти кэш браузера (Ctrl+Shift+Delete)
- Проверь CORS в `app/main.py`

### Нет данных на карте
- Проверь БД: `sqlite3 app/petrol.db "SELECT COUNT(*) FROM stations;"`
- Запусти загрузчик: `python scripts/load_data.py`
- Проверь логи сервера

### Фильтры не работают
- Откройся в Chrome DevTools (F12)
- Проверь Network tab → `/api/stations`
- Проверь что параметры передаются

### APK не устанавливается
- Включи "Unknown sources" в Settings → Security
- Проверь версию Android (минимум Android 6.0)
- Удали старую версию перед установкой новой

## Развертывание обновлений

1. Исправь код локально
2. `git push origin master`
3. GitHub Actions автоматически протестирует
4. Render автоматически перезагрузит сервер
5. Пересобери APK в PWABuilder
