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

## Фазы разработки

- Phase 0 ✅ — Разведка источников
- Phase 1 ✅ — Скелет (текущая)
- Phase 2 — Загрузчики данных (OSM, fuelprice)
- Phase 3 — API endpoints
- Phase 4 — Фронт (карта)
- Phase 5 — Полиш и деплой
