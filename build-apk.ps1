# Скрипт сборки APK для Petrol на Windows
# Запустить: powershell -ExecutionPolicy Bypass -File build-apk.ps1

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "   PETROL - Сборка APK с Газпромнефтью" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Проверяем Python
Write-Host "1. Проверка Python..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "   ✗ Python не установлен" -ForegroundColor Red
    Write-Host "   Установите Python: https://www.python.org/downloads/" -ForegroundColor Red
    exit 1
}
Write-Host "   ✓ $pythonVersion" -ForegroundColor Green
Write-Host ""

# Проверяем зависимости
Write-Host "2. Проверка зависимостей..." -ForegroundColor Yellow
$requiredPackages = @("fastapi", "uvicorn", "sqlalchemy", "httpx")
foreach ($pkg in $requiredPackages) {
    python -c "import $pkg" 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✓ $pkg" -ForegroundColor Green
    } else {
        Write-Host "   ✗ $pkg не найден" -ForegroundColor Red
        Write-Host "   Установите: pip install -r requirements.txt" -ForegroundColor Yellow
        exit 1
    }
}
Write-Host ""

# Проверяем фронтенд
Write-Host "3. Проверка фронтенда..." -ForegroundColor Yellow
$htmlFile = "static\index.html"
if (-Not (Test-Path $htmlFile)) {
    Write-Host "   ✗ Файл $htmlFile не найден" -ForegroundColor Red
    exit 1
}

$htmlContent = Get-Content $htmlFile -Raw
if ($htmlContent -match "gazpromBtn") {
    Write-Host "   ✓ Кнопка Газпромнефть найдена" -ForegroundColor Green
} else {
    Write-Host "   ✗ Кнопка Газпромнефть НЕ найдена" -ForegroundColor Red
    exit 1
}

if ($htmlContent -match "loadGazpromStations") {
    Write-Host "   ✓ Функция loadGazpromStations найдена" -ForegroundColor Green
} else {
    Write-Host "   ✗ Функция loadGazpromStations НЕ найдена" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Запускаем сервер
Write-Host "4. Запуск сервера..." -ForegroundColor Yellow
Write-Host "   Сервер запущен на http://localhost:8000" -ForegroundColor Cyan
Write-Host ""
Write-Host "5. ДАЛЕЕ В БРАУЗЕРЕ:" -ForegroundColor Yellow
Write-Host "   a) Откройте https://www.pwabuilder.com" -ForegroundColor Cyan
Write-Host "   b) Загрузите URL: http://localhost:8000" -ForegroundColor Cyan
Write-Host "   c) Нажмите 'Start'" -ForegroundColor Cyan
Write-Host "   d) Выберите 'Android'" -ForegroundColor Cyan
Write-Host "   e) Нажмите 'Build'" -ForegroundColor Cyan
Write-Host "   f) Скачайте petrol.apk" -ForegroundColor Cyan
Write-Host ""
Write-Host "6. УСТАНОВКА НА ТЕЛЕФОН:" -ForegroundColor Yellow
Write-Host "   adb install -r petrol.apk" -ForegroundColor Cyan
Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host ""

# Запускаем
Write-Host "Нажмите CTRL+C чтобы остановить сервер" -ForegroundColor Yellow
Write-Host ""

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

