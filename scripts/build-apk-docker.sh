#!/bin/bash
# Сборка APK через Docker контейнер

set -e

echo "=== Petrol: Сборка APK через Docker ==="
echo ""

# Проверяем Docker
if ! command -v docker &> /dev/null; then
    echo "✗ Docker не установлен"
    echo "Установите Docker: https://www.docker.com/products/docker-desktop"
    exit 1
fi

echo "✓ Docker найден: $(docker --version)"
echo ""

# Собираем образ
echo "1. Сборка Docker образа..."
docker build -t petrol:latest .
echo "✓ Образ собран"
echo ""

# Запускаем контейнер
echo "2. Запуск контейнера..."
echo "   Контейнер запущен на http://localhost:8000"
echo ""

echo "3. Откройте в браузере:"
echo "   https://www.pwabuilder.com"
echo ""
echo "4. Загрузите URL:"
echo "   http://localhost:8000"
echo ""
echo "5. Build → Android → Download APK"
echo ""
echo "6. Установите на телефон:"
echo "   adb install -r petrol.apk"
echo ""

# Запускаем
docker run -p 8000:8000 petrol:latest

