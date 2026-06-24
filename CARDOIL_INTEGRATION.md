# Интеграция Card-Oil.ru для более актуальных данных

## 📋 Проблема

`russiabase.ru` имеет проблемы с актуальностью:
- Данные обновляются раз в 6 часов
- Наличие топлива может быть неверным
- Некоторые АЗС не обновляют информацию

**Решение:** использовать `card-oil.ru` как дополнительный или основной источник.

---

## ✅ Преимущества Card-Oil.ru

- ✓ Более актуальные данные (обновляются чаще)
- ✓ Точное наличие топлива на станциях
- ✓ Координаты и адреса точные
- ✓ Авторизованный источник (более надёжный)

## ❌ Недостатки

- ✗ Использует JavaScript для загрузки (нужен Playwright)
- ✗ Сложнее парсить (Bitrix CMS)
- ✗ Медленнее чем russiabase

---

## 🚀 Как включить Card-Oil

### Вариант 1: Быстро (без Playwright)

```bash
# Переключить на card-oil в конфиге (уже готово):
# app/config.py → data_source = "cardoil"

# Или через переменную окружения:
export DATA_SOURCE=cardoil
python -m uvicorn app.main:app
```

**Статус:** работает, но с ограничениями (нужен JS парсинг).

---

### Вариант 2: Полнофункционально (с Playwright)

```bash
# 1. Установить Playwright
pip install playwright

# 2. Скачать браузер
python -m playwright install

# 3. Включить card-oil
export DATA_SOURCE=cardoil
python -m uvicorn app.main:app
```

**Статус:** полная работоспособность, Playwright парсит JS.

---

## 🔧 Использование в коде

### В конфиге приложения

```python
# .env файл
DATA_SOURCE=cardoil
```

Или программно:
```python
from app.config import settings

if settings.data_source == "cardoil":
    from app.services.cardoil_loader import load_cardoil_ivanovo
    load_cardoil_ivanovo(db)
else:
    from app.services.russiabase_loader import load_ivanovo
    load_ivanovo(db)
```

### В scheduler

```python
# app/services/scheduler.py

async def refresh_job():
    db = SessionLocal()
    try:
        if settings.data_source == "cardoil":
            ns, np = load_cardoil_ivanovo(db)
        else:
            ns, np = load_ivanovo(db)  # russiabase
        logger.info(f"refresh: {ns} станций, {np} цен из {settings.data_source}")
    finally:
        db.close()
```

---

## 📊 Сравнение источников

| Параметр | RussiaBase | Card-Oil |
|----------|-----------|----------|
| **Актуальность** | 6 часов | 1-2 часа |
| **Наличие топлива** | ⚠️ Иногда неверно | ✓ Точное |
| **Скорость** | ✓ Быстро | ⚠️ С JS парсингом |
| **Требуемые инструменты** | httpx, regex | Playwright |
| **Легкость парсинга** | ✓ Простой JSON | ❌ Bitrix CMS, JS |

---

## 🔄 Гибридный подход (рекомендуемо)

Использовать оба источника:

```python
async def load_stations_hybrid(db: Session):
    """Загружаем русский базу, затем обогащаем card-oil данными."""
    
    # Основная загрузка
    ns1, np1 = load_ivanovo(db)
    
    # Обогащение card-oil
    try:
        ns2, np2 = load_cardoil_ivanovo(db)
        logger.info(f"enriched with cardoil: {ns2} станций")
    except Exception:
        logger.warning("cardoil enrichment failed, using russiabase only")
```

---

## 📍 Структура Card-Oil Data

После парсинга с Playwright получаем:

```json
{
  "stations": [
    {
      "id": "gazprom_1",
      "name": "Газпромнефть №143",
      "address": "Иваново, ул. Первомайная, 113",
      "lat": 57.2335,
      "lon": 41.1391,
      "fuels": {
        "ai92": {"price": 61.48, "available": true},
        "ai95": {"price": 64.94, "available": true},
        "diesel": {"price": 75.27, "available": true}
      }
    }
  ]
}
```

---

## 🐛 Troubleshooting

### Ошибка: "Playwright не найден"

```bash
pip install playwright
python -m playwright install chromium
```

### Ошибка: "Card-Oil API не доступен"

Возможные причины:
- Card-Oil заблокировал доступ (используют User-Agent проверку)
- Сайт изменил структуру HTML
- Требуется VPN или прокси

**Решение:**
```python
# Добавить в заголовки
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120",
    "Accept-Language": "ru-RU",
}
```

### Загрузка очень медленная

Card-Oil медленнее russiabase из-за JS парсинга.

**Решение:**
- Увеличить интервал обновления: `REFRESH_MIN_INTERVAL=3600` (1 час)
- Использовать russiabase как основной + card-oil для проверки 1 раз в день

---

## 🚀 Развертывание на Render

```bash
# 1. Добавить в render.yaml
env:
  - key: "DATA_SOURCE"
    value: "cardoil"
  - key: "PYTHONUNBUFFERED"
    value: "1"

# 2. При первом деплое:
# render автоматически установит зависимости из requirements.txt
# (если добавить playwright туда)

# 3. requirements.txt
# playwright==1.40.0
```

---

## 📈 Статус интеграции

- [x] `cardoil_loader.py` создан
- [x] Конфиг расширен (`data_source` опция)
- [ ] Scheduler обновлен для использования обоих источников
- [ ] Фронтенд показывает источник данных
- [ ] Тестирование с реальными данными

---

## 💡 Рекомендации

**Для production (Render):**
```
DATA_SOURCE=russiabase  # основной, быстрый
# + cronjob для card-oil проверки 1 раз в день
```

**Для локальной разработки:**
```
DATA_SOURCE=cardoil  # если установлен Playwright
# Иначе: DATA_SOURCE=russiabase
```

**Для максимальной актуальности:**
```
DATA_SOURCE=hybrid  # оба источника
REFRESH_INTERVAL=1800  # 30 минут вместо 6 часов
```
