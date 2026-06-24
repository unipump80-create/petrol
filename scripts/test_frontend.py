#!/usr/bin/env python
"""Проверка фронтенда: убедиться что кнопка Газпромнефть видна в HTML."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Читаем фронтенд
html_path = Path(__file__).parent.parent / "static" / "index.html"
html_content = html_path.read_text(encoding='utf-8')

print("=== Проверка фронтенда ===\n")

# Проверка 1: Кнопка Газпромнефть
if 'gazpromBtn' in html_content:
    print("✓ Кнопка Газпромнефть найдена в HTML")
else:
    print("✗ ОШИБКА: Кнопка Газпромнефть НЕ найдена!")
    sys.exit(1)

# Проверка 2: Функция loadGazpromStations
if 'loadGazpromStations' in html_content:
    print("✓ Функция loadGazpromStations найдена")
else:
    print("✗ ОШИБКА: Функция loadGazpromStations НЕ найдена!")
    sys.exit(1)

# Проверка 3: API endpoint
if '/prices/gazprom/locations' in html_content:
    print("✓ API endpoint /prices/gazprom/locations найден")
else:
    print("✗ ОШИБКА: API endpoint НЕ найден!")
    sys.exit(1)

# Проверка 4: Переменная showOnlyGazprom
if 'showOnlyGazprom' in html_content:
    print("✓ Переменная showOnlyGazprom найдена")
else:
    print("✗ ОШИБКА: Переменная showOnlyGazprom НЕ найдена!")
    sys.exit(1)

# Проверка 5: Обработчик кнопки
if "document.getElementById('gazpromBtn').onclick" in html_content:
    print("✓ Обработчик onclick для кнопки найден")
else:
    print("✗ ОШИБКА: Обработчик onclick НЕ найден!")
    sys.exit(1)

print("\n✓ Все проверки пройдены!\n")

# Размер HTML
size_kb = len(html_content) / 1024
print(f"Размер HTML: {size_kb:.1f} KB")

# Подсчёт строк
lines = len(html_content.split('\n'))
print(f"Строк в файле: {lines}")

print("\n🎉 Фронтенд готов к сборке APK!")
print("\nСледующие шаги:")
print("1. python -m uvicorn app.main:app --port 8000")
print("2. Открыть http://localhost:8000 в браузере")
print("3. Проверить что видна кнопка 🔵 Газпромнефть")
print("4. Нажать кнопку и убедиться что данные загружаются")
print("5. На PWABuilder собрать APK")
