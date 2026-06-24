#!/bin/bash
# Скрипт для сборки APK Petrol с Газпромнефтью

set -e  # Exit on error

echo "==================================================================="
echo "   PETROL - Сборка Android APK с интеграцией Газпромнефти"
echo "==================================================================="
echo ""

# Проверяем зависимости
echo "1. Проверка зависимостей..."

if ! command -v node &> /dev/null; then
    echo "   ✗ Node.js не установлен"
    echo "   Установите: https://nodejs.org/"
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo "   ✗ npm не установлен"
    exit 1
fi

echo "   ✓ Node.js $(node --version)"
echo "   ✓ npm $(npm --version)"
echo ""

# Инициализируем Capacitor если его нет
echo "2. Подготовка проекта..."

if [ ! -d "node_modules" ]; then
    echo "   → Установка npm пакетов..."
    npm install -g @capacitor/cli @capacitor/core @capacitor/android
fi

if [ ! -f "capacitor.config.json" ]; then
    echo "   → Инициализирую Capacitor..."
    npx cap init "Petrol" "com.petrol.ivanovo" --web-dir static
fi

echo "   ✓ Проект готов"
echo ""

# Копируем веб-приложение
echo "3. Подготовка веб-приложения..."
if [ -d "static" ]; then
    echo "   ✓ Статические файлы найдены"
else
    echo "   ✗ Папка static не найдена"
    exit 1
fi

# Проверяем что Газпромнефть в фронтенде
if grep -q "gazpromBtn" static/index.html; then
    echo "   ✓ Кнопка Газпромнефть найдена в фронтенде"
else
    echo "   ✗ Кнопка Газпромнефть НЕ найдена"
    exit 1
fi

echo ""

# Собираем Android приложение
echo "4. Сборка Android приложения..."
echo ""
echo "   Требуется Android Studio или Android SDK"
echo "   Если у вас установлены:"
echo "   - ANDROID_HOME (переменная окружения)"
echo "   - Android SDK"
echo "   - Gradle"
echo ""
echo "   То выполните в отдельном терминале:"
echo ""
echo "   bash"
echo "   export ANDROID_HOME=\$HOME/Android/Sdk"
echo "   export PATH=\$PATH:\$ANDROID_HOME/tools:\$ANDROID_HOME/platform-tools"
echo "   cd $(pwd)/android"
echo "   ./gradlew assembleDebug"
echo ""
echo "   Или используйте Web:"
echo "   https://www.pwabuilder.com → Загрузить http://localhost:8001"
echo ""

echo "==================================================================="
echo "   Файл APK будет в:"
echo "   android/app/build/outputs/apk/debug/app-debug.apk"
echo ""
echo "   Установка на телефон:"
echo "   adb install -r app-debug.apk"
echo "==================================================================="
echo ""
