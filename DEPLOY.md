# Развёртывание Petrol и сборка APK

## Вариант 1: Heroku (бесплатный, 1 дайно)

```bash
# Если нет аккаунта: https://heroku.com, auth, создать app
heroku login
heroku create petrol-ivanovo
git push heroku main
heroku open
```

URL хоста: `https://petrol-ivanovo.herokuapp.com`

## Вариант 2: Render (бесплатный, постоянный)

1. https://render.com
2. New → Web Service
3. Connect Git repo (выбери этот)
4. Name: `petrol`, Runtime: Python, Build: `pip install -r requirements.txt`, Start: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
5. Deploy

URL: `https://petrol-xxxxx.onrender.com`

## Вариант 3: Docker локально (для тестирования)

```bash
docker build -t petrol .
docker run -p 8000:8000 petrol
# http://localhost:8000
```

## Собрать APK

1. Получить публичный URL хоста (Heroku, Render или localhost с ngrok)
2. Перейти: https://www.pwabuilder.com
3. Загрузить URL → Analyze
4. Build → Android → Download .apk
5. Установить на телефон

## Если localhost

```bash
# В отдельном терминале:
ngrok http 8000
# Скопировать https://xxxxx.ngrok.io
```
