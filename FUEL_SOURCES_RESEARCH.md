# Исследование источников наличия топлива

> Дата: 2026-06-26. Метод: веб-поиск + прямое зондирование API (харнесс-исследование).
> Цель: найти источники данных о **наличии** топлива на АЗС (есть/нет/очереди/лимиты), не только цены.

## Уже подключено в petrol

| Источник | Домен | Что даёт |
|---|---|---|
| Benzuber | app.benzuber.ru | цены, статус работы АЗС |
| CardOil | card-oil.ru | цены, сеть CardOil |
| Газпромнефть | (gazprom_loader) | цены/наличие сети ГПН |
| RussiaBase | russiabase.ru | цены по АЗС |
| OSM | overpass-api.de | геолокации АЗС |

## Новые источники (найдено)

### 1. ⭐ ГдеБЕНЗ — gdebenz.ru — РЕКОМЕНДУЕТСЯ
Краудсорсинговая карта наличия топлива. **Бесплатно, без авторизации, FastAPI (JSON).**

**Ключевой эндпоинт — наличие:**
```
GET https://gdebenz.ru/api/nearby?lat=57.0&lon=40.97
```
```json
{
  "summary": {"yes": 2, "queue": 0, "low": 0, "no": 38},
  "stations": [
    {"osm_id":"4757614870","status":"no","confirmations":10,
     "confirmed":true,"last_at":"2026-06-26 06:06:00",
     "lat":57.0075,"lon":40.9706,"distance_km":0.8}
  ]
}
```
- `status`: **yes / queue / low / no** — прямое наличие топлива
- `confirmations`, `confirmed`, `last_at` — свежесть и достоверность отметки
- Идеально ложится на фичу petrol «где нет топлива».

**Прочие эндпоинты:**
- `GET /api/stations?lat1=&lon1=&lat2=&lon2=` — АЗС в bbox (osm_id, name, brand, lat, lon)
- `GET /api/comments?lat1=&lon1=&lat2=&lon2=` — комментарии водителей в bbox
- `GET /api/cities`, `GET /api/search`
- Привязка по `osm_id` совпадает с уже используемым osm_loader → лёгкий джойн.

Иваново сейчас (bbox 56.9–57.1 / 40.8–41.2): **38 «нет», 2 «есть»** — совпадает с топливным дефицитом.

### 2. Benzup — benzup.ru (бэкенд api.omt-consult.ru) — нужен ключ
Структурированный API цен и справочника АЗС (РФ/КЗ/КГ).
```
GET https://api.omt-consult.ru/v2/stations   → 403 (требуется авторизация)
        /v2/products, /v2/bulk/stations, /v2/trucks
```
Богатые данные, но закрыт — нужен ключ/договор. Кандидат на коммерческую интеграцию.

### 3. Где бензин? — gdebenzin.org
Карта статусов АЗС (зелёный/жёлтый/красный = достаточно/ограничения/не работает). Открытого API при зондировании не выявлено — вероятно, потребуется парсинг.

### 4. MultiGO — business.multigo.ru
Данные АЗС + цены (бензин/ДТ/газ), цветовая индикация выгоды. Топливные карты; публичного API не подтверждено.

### 5. Transcards — transcards.ru
Мобильное приложение топливных карт. Для конечного наличия менее релевантно.

## Рекомендация

1. **Внедрить ГдеБЕНЗ `api/nearby`** новым лоадером `gdebenz_loader.py` — это прямой бесплатный источник наличия (`status` yes/queue/low/no + свежесть). Джойн по `osm_id` с существующими станциями.
2. Учитывать `confirmations`/`last_at`: показывать только подтверждённые и свежие отметки (TTL, напр. 6–12 ч).
3. Benzup/omt-consult — отложить до получения ключа (платный/структурированный).
4. gdebenzin.org / MultiGO — резерв через парсинг, если нужна перекрёстная валидация.

## Источники
- https://gdebenz.ru/ (+ api/nearby, api/stations)
- https://benzup.ru/api (api.omt-consult.ru)
- https://www.gdebenzin.org/
- https://business.multigo.ru/
- https://hi-tech.mail.ru/news/149872-kak-proverit-nalichie-topliva-na-azs-populyarnye-servisy/
