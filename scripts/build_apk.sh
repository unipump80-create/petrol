#!/bin/bash
# Сборка APK через PWABuilder API (требует node)
# Использование: ./scripts/build_apk.sh https://petrol-ivanovo.herokuapp.com

if [ -z "$1" ]; then
  echo "Usage: $0 <url>"
  echo "Example: $0 https://petrol-ivanovo.herokuapp.com"
  exit 1
fi

URL="$1"
WORK_DIR="/tmp/petrol-apk"
mkdir -p "$WORK_DIR"
cd "$WORK_DIR"

echo "Building APK for $URL..."

# Используем PWABuilder CLI (если установлен)
if command -v pwabuilder &> /dev/null; then
  pwabuilder "$URL" --outputDirectory . --platforms android
  echo "APK готов в $WORK_DIR"
else
  echo "pwabuilder не установлен. Установи:"
  echo "  npm install -g @pwabuilder/pwabuilder"
  echo "Потом:"
  echo "  $0 $URL"
  exit 1
fi
