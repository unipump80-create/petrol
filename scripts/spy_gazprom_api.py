#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Исследование API Газпром нефти для поиска endpoint'ов АЗС."""
import asyncio
import sys
import io
from playwright.async_api import async_playwright

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Логируем все сетевые запросы
        requests = []
        def log_request(request):
            url = request.url
            if any(x in url for x in ['api', 'service', 'ajax', 'station', 'azs', '/v']):
                print(f"[API] {request.method} {url[:100]}")
                requests.append({'method': request.method, 'url': url})

        page.on('request', log_request)

        print("[*] Открываю Газпром нефть приложение...")
        await page.goto("https://www.gazprom-neft.ru/app/", wait_until="networkidle", timeout=30000)

        print("[*] Ищу АЗС в Иваново...")
        try:
            await page.fill("input", "Иваново", timeout=5000)
            await page.wait_for_timeout(3000)
        except:
            print("[!] Поле города не найдено, ждём загрузки...")
            await page.wait_for_timeout(5000)

        print(f"\n[RESULT] Найдено {len(requests)} API запросов:")
        for req in requests[-10:]:  # Последние 10
            print(f"  {req['method']} {req['url']}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
