# CLAUDE.md — petrol

## Авто-обновление на Android (ОБЯЗАТЕЛЬНО)

> После любых правок кода/статики petrol — **автоматически** деплоить, не дожидаясь отдельной просьбы.

Android-приложение — PWA-обёртка над прод-сервером на Render
(**petrol-1oz7.onrender.com**, репо github.com/unipump80-create/petrol, ветка `master`).
Версия кэша service worker = git-хеш деплоя (`_resolve_version` в `app/main.py`):
каждый push → новый хеш → SW видит новую версию → на телефоне всплывает баннер
**«Обновить приложение»**.

**Порядок после завершения правок:**
1. Проверить локально (syntax + сервер на :8001 поднимается).
2. `git add <изменённые файлы по имени>` (не `git add .`).
3. `git commit -m "..."` (+ `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`).
4. `git push origin master` → Render автодеплоит.
5. Дождаться, что `/version` на проде показывает новый хеш (фоновый `until`).

Без push изменения **не попадут на Android** — пользователю придётся просить вручную.
Поэтому push после завершённой правки — часть задачи, а не отдельный шаг.

## Источники данных
Цены/наличие: russiabase, benzuber, cardoil, gazprom, **gdebenz** (наличие, см.
`FUEL_SOURCES_RESEARCH.md`). OSM — геолокации/часы. Наличие топлива («где нет
топлива») идёт из ГдеБЕНЗ (`gdebenz_loader`), ручные кнопки-репорты убраны.

## Запуск
- Прод: `uvicorn app.main:app --host 0.0.0.0 --port 8000` (Render).
- Локально (8000 занят агентом UNIPUMP): порт **8001**.
- `python -m uvicorn app.main:app --port 8001` (нужен `PYTHONPATH=.`).
