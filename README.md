# Petrol — мониторинг цен на топливо г. Иваново

Сервер для розничных пользователей (водителей): поиск дешёвого топлива и информация о наличии на АЗС города.

## Быстрый старт

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/unipump80-create/petrol)

Или развернуть локально:
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Затем в PWABuilder: https://www.pwabuilder.com → URL → Build Android → Download APK

## Стек

- Python 3.12
- FastAPI + Uvicorn
- SQLAlchemy + SQLite
- APScheduler (парсинг по расписанию)
- httpx + selectolax (парсинг)

## Установка

```bash
pip install -r requirements.txt
cp .env.example .env
```

## Запуск

```bash
python run.ps1
# или
python -m uvicorn app.main:app --reload
```

Сервер: `http://localhost:8000`
- GET `/` — приветствие
- GET `/health` — статус
- GET `/prices/summary` — сводка по городу (мин/средн/макс)
- GET `/prices/gazprom/availability` — доступность топлива на Газпромнефти
- GET `/prices/gazprom/locations` — все локации Газпромнефти с ценами

## Структура

```
petrol/
├── app/
│   ├── main.py          — FastAPI приложение
│   ├── config.py        — конфигурация
│   ├── database.py      — подключение к БД
│   ├── models.py        — SQLAlchemy модели
│   ├── routers/         — endpoints
│   └── services/        — логика (парсеры, загрузчики)
├── scripts/             — утилиты
├── plans/               — технические планы
└── requirements.txt
```

## Источники данных

- **RussiaBase** (основной) — 51 АЗС Иванова, обновление каждые 6 часов
- **Card-Oil.ru** (опциональный) — более свежие данные о наличии топлива
- **OpenStreetMap** (обогащение) — часы работы, улучшенные координаты

Выбор источника: `DATA_SOURCE=russiabase|cardoil`

## Фазы разработки

- Phase 0 ✅ — Разведка источников
- Phase 1 ✅ — Скелет
- Phase 2 ✅ — Загрузчики данных (RussiaBase, Card-Oil, OSM)
- Phase 3 ✅ — API endpoints (51 АЗС + 15 Газпромнефть)
- Phase 4 ✅ — Фронт (карта, фильтры, обновления)
- Phase 5 ✅ — Полиш (версионирование, PWA, обновления приложения)
