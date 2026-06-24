# Card-Oil.ru — все бренды АЗС

## Поддерживаемые бренды

Card-Oil.ru содержит информацию по всем основным брендам АЗС в России.

### Бренды в Иванове

- ✅ **Газпромнефть** (gazpromneft) — 15+ станций
- ✅ **Лукойл** (lukoil) — 12+ станций
- ✅ **Татнефть** (tatnefit) — доступна
- ✅ **Сургутнефтегаз** (surgutneftegaz) — доступна
- ✅ **Роснефть** (rosneft) — доступна
- ✅ **Итера** (itera) — доступна
- ✅ **Esso** (esso) — доступна
- ✅ **Shell** (shell) — доступна
- ✅ **Азнефть** (azneft) — доступна

## Структура URL

```
https://card-oil.ru/azs/{brand}/{city}/
```

**Примеры:**
- Газпромнефть в Иванове: `https://card-oil.ru/azs/gazpromneft/ivanovo/`
- Лукойл в Иванове: `https://card-oil.ru/azs/lukoil/ivanovo/`
- Газпромнефть в Москве: `https://card-oil.ru/azs/gazpromneft/moscow/`

## Как использовать

### Вариант 1: Card-Oil данные вместо RussiaBase

```bash
# Установить Playwright
pip install playwright
python -m playwright install

# Использовать card-oil как источник
DATA_SOURCE=cardoil
python -m uvicorn app.main:app
```

### Вариант 2: Загрузить все бренды

```python
from app.database import SessionLocal
from app.services.cardoil_loader import load_cardoil_all_brands

db = SessionLocal()
stations, prices = load_cardoil_all_brands(db, city='ivanovo')
print(f"Загружено: {stations} станций")
```

### Вариант 3: Гибридный подход

```python
# Сначала RussiaBase (быстро)
load_ivanovo(db)

# Потом Card-Oil для обогащения (более свежие данные)
load_cardoil_all_brands(db)
```

## Данные о наличии топлива

Card-Oil.ru показывает **точное наличие топлива**:
- Какой вид топлива доступен
- Текущие цены по каждому виду
- Время последнего обновления

RussiaBase в сравнении:
- Обновляется раз в 6 часов
- Иногда данные неточные

**Вывод:** Card-Oil.ru лучше для актуальности, RussiaBase лучше для скорости.

## Требования

### Без Playwright
- ✅ Работает быстро
- ❌ Парсинг HTML без JS (неполные данные)
- ❌ Требуется обратный инжиниринг

### С Playwright
- ✅ Полные данные
- ✅ JS рендеринг
- ❌ Медленнее (нужно запускать браузер)
- ❌ Требует ресурсы

## Города

Card-Oil.ru доступна для всех основных городов:
- moscow
- spb (Санкт-Петербург)
- ivanovo (Иваново)
- novosibirsk
- ekaterinburg
- и т.д.

## Производительность

**RussiaBase:** 51 АЗС за 1 сек
**Card-Oil (с Playwright):** 15 АЗС за 30+ сек

**Рекомендация:**
- Production: RussiaBase (основной)
- Ночные обновления: Card-Oil (для актуальности)
- Локальная разработка: Card-Oil (с Playwright)

## Интеграция

```bash
# Переключиться на Card-Oil
echo "DATA_SOURCE=cardoil" >> .env

# Или через переменную
export DATA_SOURCE=cardoil
python -m uvicorn app.main:app
```

## API endpoints

```bash
# Текущий источник
curl https://petrol-1oz7.onrender.com/prices/source

# Все АЗС (из текущего источника)
curl https://petrol-1oz7.onrender.com/stations

# Статистика
curl https://petrol-1oz7.onrender.com/prices/stats
```

## Установка Playwright на Render

Добавить в `render.yaml`:
```yaml
buildCommand: pip install -r requirements.txt && python -m playwright install
```

Или в `requirements.txt`:
```
playwright==1.40.0
```

## Что дальше?

- [ ] Полная интеграция всех брендов
- [ ] Кэширование историй цен
- [ ] Сравнение источников (RussiaBase vs Card-Oil)
- [ ] Уведомления о резких изменениях цен
- [ ] Экспорт данных по брендам
