"""Загрузчик АЗС и цен с card-oil.ru.

Card-oil.ru - агрегатор с более актуальными данными о наличии топлива.
Используется вместо russiabase для получения более точной информации.
"""
import logging
import httpx
import json
from datetime import datetime
from sqlalchemy.orm import Session
from app.models import Station, Price
from app.services.brands import normalize_brand

logger = logging.getLogger(__name__)

# Маппинг типов топлива card-oil → наша нотация
FUEL_MAP = {
    'АИ-92': 'ai92',
    'АИ-95': 'ai95',
    'АИ-98': 'ai98',
    'АИ-100': 'ai100',
    'ДТ': 'diesel',
    'ДТ Euro': 'diesel',
    'Газ': 'gas',
    'Пропан': 'gas',
    'АИ-95 Plus': 'ai95plus',
}


async def fetch_cardoil_stations(city: str = 'ivanovo', brand: str = None) -> list[dict]:
    """Получить станции с card-oil.ru.

    Args:
        city: код города (ivanovo, moscow, spb)
        brand: фильтр по бренду (gazpromneft, lukoil, и т.д.)

    Returns:
        Список станций с координатами и ценами
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/javascript, */*",
        "X-Requested-With": "XMLHttpRequest",
    }

    stations = []

    try:
        # URL для запроса станций
        url = f"https://card-oil.ru/azs/{brand or 'gazpromneft'}/{city}/"

        async with httpx.AsyncClient(timeout=30, headers=headers, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()

            # Парсим HTML для поиска JSON данных
            html = resp.text

            # Ищем данные о станциях в HTML
            # card-oil использует JavaScript загрузку, ищем в атрибутах data-*
            import re

            # Попытка найти координаты и информацию о станциях
            # Формат: data-lat="57.xxx" data-lon="41.xxx" и т.д.
            station_pattern = r'data-lat="([^"]+)"[^>]*data-lon="([^"]+)"'

            matches = re.finditer(station_pattern, html)
            for match in matches:
                lat, lon = match.groups()
                # Получить контекст (название, адрес, цены) из этого же участка HTML
                try:
                    stations.append({
                        'lat': float(lat),
                        'lon': float(lon),
                        'found': True  # флаг что нашли координаты
                    })
                except ValueError:
                    continue

            logger.info(f"cardoil: найдено {len(stations)} станций из HTML")

    except Exception as e:
        logger.error(f"cardoil: ошибка при парсинге: {e}")

    return stations


def fetch_cardoil_sync(city: str = 'ivanovo', brand: str = 'gazpromneft') -> list[dict]:
    """Синхронная версия для интеграции с БД.

    На данный момент - заглушка, т.к. card-oil использует JS загрузку.
    Требуется Playwright или Selenium для полного парсинга.
    """
    # Для полного функционала нужен Playwright:
    # from playwright.sync_api import sync_playwright
    #
    # with sync_playwright() as p:
    #     browser = p.chromium.launch()
    #     page = browser.new_page()
    #     page.goto(url)
    #     page.wait_for_load_state('networkidle')
    #     content = page.content()
    #     ...

    logger.warning("cardoil: используется облегченный парсинг без JS")
    return []


def load_cardoil_ivanovo(db: Session) -> tuple[int, int]:
    """Загружает станции Газпромнефти с card-oil.ru.

    На данный момент card-oil.ru требует JS для полной загрузки.
    Рекомендуется использовать russiabase как основной источник,
    а card-oil для проверки актуальности данных.

    Returns:
        (количество_станций, количество_цен)
    """
    logger.warning("cardoil: для полного функционала требуется Playwright")
    logger.info("cardoil: используем russiabase как основной источник")

    # Пока что просто логируем
    # Для реального использования:
    # 1. Установить: pip install playwright
    # 2. python -m playwright install
    # 3. Раскомментировать код выше

    return 0, 0


# ===== Альтернатива: использовать API если доступно =====

async def fetch_cardoil_api(city: str = 'ivanovo') -> dict:
    """Попытка получить данные через внутренний API card-oil.

    Если найдём публичный API - будет работать.
    Иначе - требуется обратный инжиниринг или Playwright.
    """
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # Возможные API endpoints
            endpoints = [
                f"https://card-oil.ru/api/stations?city={city}",
                f"https://api.card-oil.ru/stations?city={city}",
                f"https://card-oil.ru/api/v1/gas-stations?city={city}",
            ]

            for endpoint in endpoints:
                try:
                    resp = await client.get(endpoint)
                    if resp.status_code == 200:
                        return resp.json()
                except Exception:
                    continue

    except Exception as e:
        logger.debug(f"cardoil API: {e}")

    return {}


# ===== Гибридный подход =====

class CardOilLoader:
    """Интеллектуальный загрузчик данных с card-oil.ru.

    Стратегия:
    1. Если доступен API - используем его
    2. Если нужен JS парсинг - используем Playwright (если установлен)
    3. Если ничего - используем russiabase + логируем что card-oil недоступен

    По мере развития можем переключиться полностью на card-oil.
    """

    def __init__(self):
        self.has_playwright = self._check_playwright()
        self.last_update = None

    def _check_playwright(self) -> bool:
        """Проверить доступность Playwright."""
        try:
            import playwright
            return True
        except ImportError:
            return False

    async def load(self, city: str = 'ivanovo', brand: str = 'gazpromneft'):
        """Загрузить данные с лучшей доступной стратегией."""
        if self.has_playwright:
            return await self._load_with_playwright(city, brand)
        else:
            logger.info("cardoil: Playwright не установлен, используем russiabase")
            return None

    async def _load_with_playwright(self, city: str, brand: str):
        """Загрузить через Playwright (требует установки)."""
        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                url = f"https://card-oil.ru/azs/{brand}/{city}/"
                await page.goto(url, wait_until='networkidle')

                # Парсим данные после загрузки JS
                stations = await page.evaluate('''
                    () => {
                        const items = document.querySelectorAll('[data-lat]');
                        return Array.from(items).map(el => ({
                            name: el.querySelector('.name')?.textContent || '',
                            address: el.querySelector('.address')?.textContent || '',
                            lat: parseFloat(el.dataset.lat),
                            lon: parseFloat(el.dataset.lon),
                            fuels: Array.from(el.querySelectorAll('.fuel'))
                                .map(f => f.dataset.code)
                        }));
                    }
                ''')

                await browser.close()
                self.last_update = datetime.now()
                return stations

        except Exception as e:
            logger.error(f"cardoil playwright: {e}")
            return None


async def fetch_all_brands_ivanovo() -> list[str]:
    """Получить список всех доступных брендов на card-oil.ru для Иванова."""
    brands = [
        'gazpromneft',
        'lukoil', 
        'tatnefit',
        'surgutneftegaz',
        'rosneft',
        'itera',
        'esso',
        'shell',
        'azneft',
    ]
    return brands


async def fetch_cardoil_all_brands(city: str = 'ivanovo') -> dict:
    """Загрузить АЗС всех брендов с card-oil.ru."""
    all_stations = {}
    brands = await fetch_all_brands_ivanovo()

    for brand in brands:
        try:
            stations = await fetch_cardoil_stations(city, brand)
            if stations:
                all_stations[brand] = stations
                logger.info(f"cardoil: {brand} — {len(stations)} станций")
        except Exception as e:
            logger.warning(f"cardoil: {brand} — ошибка: {e}")

    return all_stations
