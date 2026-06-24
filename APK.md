# APK для Android

**Petrol** — PWA (Progressive Web App). На Android это полноценное приложение с иконкой, без браузерной панели.

## Как получить APK

### Быстро (5 минут)

1. Деплой хоста:
   - **Heroku**: `heroku create petrol-ivanovo && git push heroku main`
   - **Render**: нажать кнопку в их UI
   - Получить URL: `https://petrol-xxxxx.com`

2. Собрать APK на https://www.pwabuilder.com:
   - Загрузить URL хоста
   - Build → Android → Download
   - Установить .apk на телефон

### Сложнее (если свой сервер)

```bash
docker build -t petrol .
docker run -p 8000:8000 petrol
# Затем в PWABuilder загрузить http://localhost:8000
# (или через ngrok если телефон из другой сети)
```

## Что внутри

- ✅ Offline-first: кэш API в Service Worker
- ✅ Иконка топливной капли (192x512px)
- ✅ Манифест (standalone, dark theme)
- ✅ Адаптивная вёрстка (мобиль/планшет)
- ✅ Настраиваемый API-адрес для хостинга

## PWA vs Native

Плюсы PWA:
- Нет Google Play (нет審査, нет комиссии)
- Обновления моментальные (из браузера)
- Работает на iOS и Android

Минусы:
- Нет доступа к отправке SMS, камере (обычно не нужны)
- Зависит от браузера телефона (Chrome/Firefox)

## На iOS

Safari автоматически устанавливает как приложение:
- Открыть → Share → Add to Home Screen
