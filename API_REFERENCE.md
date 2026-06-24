# API Reference — Petrol

## Base URL
```
https://petrol-1oz7.onrender.com
```

---

## Endpoints

### 📊 Статистика и информация

#### `GET /version`
Текущая версия приложения с git-хешем
```json
{"version": "0.2.0+abc1234"}
```

#### `GET /health`
Проверка здоровья данных (валидность, полнота)
```json
{
  "total_stations": 51,
  "with_prices": 51,
  "with_coordinates": 50,
  "with_address": 49,
  "unique_fuels": ["ai92", "ai95", "diesel", "gas"],
  "health_score": 0.95
}
```

#### `GET /prices/source`
Информация об источнике данных
```json
{
  "source": "russiabase",
  "available": ["russiabase", "cardoil"],
  "russiabase": {
    "pros": ["быстро", "полные данные"],
    "cons": ["обновляется раз в 6 часов"]
  }
}
```

#### `GET /prices/stats`
Полная статистика по данным
```json
{
  "updates": {
    "fresh_1h": 45,
    "recent_6h": 6,
    "stale_24h": 0,
    "very_old": 0,
    "total": 51,
    "freshness_percent": 88.2
  },
  "brands": {
    "Газпромнефть": {"stations": 15, "prices": 90},
    "Лукойл": {"stations": 12, "prices": 48},
    ...
  },
  "fuel_availability": {
    "ai95": 100.0,
    "ai92": 98.0,
    "diesel": 95.0,
    "gas": 28.0
  }
}
```

---

### 🗺️ АЗС и цены

#### `GET /prices/summary`
Сводка по городу (мин/средн/макс)
```json
{
  "city": "Иваново",
  "stations": 51,
  "updated_at": "2026-06-24T12:00:00",
  "fuels": [
    {
      "fuel_type": "ai95",
      "fuel_name": "АИ-95",
      "avg": 65.85,
      "min": 61.48,
      "max": 66.09,
      "count": 14
    },
    ...
  ]
}
```

#### `GET /stations?fuel=ai95&sort=price`
Список АЗС с фильтрацией
```json
[
  {
    "id": 1,
    "name": "Газпромнефть №143",
    "brand": "Газпромнефть",
    "address": "Иваново, ул. Первомайная",
    "lat": 57.2335,
    "lon": 41.1391,
    "price": 61.48,
    "available": true,
    "observed_at": "2026-06-24T12:00:00"
  },
  ...
]
```

**Параметры:**
- `fuel`: ai92, ai95, ai98, ai100, diesel, gas, ai95plus
- `sort`: price (по цене), name (по названию)

#### `GET /stations/{id}`
Детальная информация о станции
```json
{
  "id": 1,
  "name": "Газпромнефть №143",
  "brand": "Газпромнефть",
  "address": "Иваново, ул. Первомайная, 113",
  "lat": 57.2335,
  "lon": 41.1391,
  "opening_hours": "24/7",
  "fuel_types": ["ai92", "ai95", "ai95plus", "diesel"],
  "prices": [
    {"fuel_type": "ai92", "price": 61.48, "observed_at": "2026-06-24T12:00:00"},
    {"fuel_type": "ai95", "price": 64.94, "observed_at": "2026-06-24T12:00:00"},
    ...
  ]
}
```

---

### 🔵 Газпромнефть

#### `GET /prices/gazprom/availability`
Статистика по Газпромнефти (наличие и цены)
```json
{
  "total_stations": 15,
  "fuel_types": {
    "ai92": {
      "stations": 14,
      "avg_price": 63.0,
      "min_price": 61.48,
      "max_price": 63.36
    },
    ...
  }
}
```

#### `GET /prices/gazprom/locations`
Все локации Газпромнефти с координатами
```json
{
  "count": 15,
  "stations": [
    {
      "id": 1,
      "name": "Газпромнефть №143",
      "address": "Иваново, ул. Первомайная, 113",
      "lat": 57.2335,
      "lon": 41.1391,
      "fuel_types": ["ai92", "ai95", "diesel"],
      "opening_hours": "24/7",
      "prices": {
        "ai92": 61.48,
        "ai95": 64.94,
        "diesel": 75.27
      }
    },
    ...
  ]
}
```

---

## Коды топлива

| Код | Название | Доступно |
|-----|----------|---------|
| ai92 | АИ-92 | ✓ 98% |
| ai95 | АИ-95 | ✓ 100% |
| ai98 | АИ-98 | ⚠️ 20% |
| ai100 | АИ-100 | ⚠️ 28% |
| diesel | Дизель | ✓ 95% |
| gas | Газ | ⚠️ 28% |
| ai95plus | АИ-95+ | ⚠️ 26% |

---

## Примеры запросов

### cURL

```bash
# Сводка по городу
curl https://petrol-1oz7.onrender.com/prices/summary

# Дешёвые АЗС
curl "https://petrol-1oz7.onrender.com/stations?fuel=ai95&sort=price"

# Газпромнефть
curl https://petrol-1oz7.onrender.com/prices/gazprom/availability

# Статистика
curl https://petrol-1oz7.onrender.com/prices/stats
```

### JavaScript

```javascript
// Загрузить данные
const response = await fetch('https://petrol-1oz7.onrender.com/prices/summary');
const data = await response.json();
console.log(data);
```

### Python

```python
import requests

response = requests.get('https://petrol-1oz7.onrender.com/prices/summary')
data = response.json()
print(data)
```

---

## Статус коды

| Код | Описание |
|-----|---------|
| 200 | OK — успешный запрос |
| 404 | Not Found — станция/данные не найдены |
| 429 | Too Many Requests — слишком частые обновления |
| 500 | Server Error — ошибка сервера |

---

## Rate Limiting

- Обновление данных: не чаще чем раз в 5 минут (300 сек)
- Запросы API: не ограничены

---

## Источники данных

**RussiaBase** (основной) — АЗС, цены, координаты, адреса. Обновление каждые 6 ч.

**Card-Oil.ru** (наличие) — точные флаги наличия топлива из статического
JSON (`cdn2.card-oil.ru/map/FilterAZS.json`), без цен. Используется для
обогащения наличия. Подробности — `CARDOIL_INTEGRATION.md`.

---

## Версионирование

Версия содержит:
- `0.2.0` — версия приложения
- `+abc1234` — git-хеш коммита (обновляется автоматически)

---

## PWA & Offline

Приложение работает offline благодаря Service Worker:
- Кэш динамических данных (prices, stations)
- Кэш оболочки (HTML, CSS, JS, иконки)
- Автоматическое обновление при изменении версии
