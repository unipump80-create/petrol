#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Автоматизированная сборка APK через PWABuilder в Chrome.

Требует: Chrome, ChromeDriver, selenium

    pip install selenium
    python scripts/build_apk_auto.py
"""
import time
import sys
import io
from pathlib import Path

# UTF-8 для Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
except ImportError:
    print("❌ Требует Selenium: pip install selenium")
    sys.exit(1)

APP_URL = "https://petrol-1oz7.onrender.com"
PWA_BUILDER = "https://www.pwabuilder.com"
DL_DIR = str(Path.home() / "Downloads")  # для сохранения APK


def main():
    options = webdriver.ChromeOptions()
    options.add_experimental_option("prefs", {
        "download.default_directory": DL_DIR,
        "download.prompt_for_download": False,
    })

    driver = webdriver.Chrome(options=options)
    try:
        print(f"🌐 Открываю {PWA_BUILDER}…")
        driver.get(PWA_BUILDER)
        time.sleep(3)

        print(f"📝 Ввожу URL: {APP_URL}…")
        input_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder*='URL']"))
        )
        input_field.clear()
        input_field.send_keys(APP_URL)
        time.sleep(1)

        print("🚀 Нажимаю Начать…")
        start_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Начать')]")
        start_btn.click()
        time.sleep(8)

        print("📦 Ищу кнопку Build…")
        build_btn = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Build')]"))
        )
        build_btn.click()
        time.sleep(3)

        print("🤖 Ищу Android…")
        android_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Android')]"))
        )
        android_btn.click()
        time.sleep(3)

        print("⬇️ Ищу Download…")
        dl_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Download')]"))
        )
        dl_btn.click()
        time.sleep(5)

        print(f"✅ APK скачивается в {DL_DIR}")
        print("⏳ Жду 30 сек для завершения…")
        time.sleep(30)

        apk_file = list(Path(DL_DIR).glob("*.apk"))[-1] if list(Path(DL_DIR).glob("*.apk")) else None
        if apk_file:
            print(f"✅ APK готов: {apk_file}")
            print("📱 Следующий шаг: загрузи на телефон и установи")
        else:
            print("⚠️ APK не найден в Downloads")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)
    finally:
        input("Нажми Enter для закрытия браузера…")
        driver.quit()


if __name__ == "__main__":
    main()
