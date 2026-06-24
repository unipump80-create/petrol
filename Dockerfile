FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# БД в /app (writable-слой контейнера), НЕ в /tmp: на Render /tmp — tmpfs.
# Данные грузятся при старте приложения (lifespan -> _ensure_data),
# поэтому build не зависит от доступности источника.
ENV DATABASE_URL=sqlite:////app/petrol.db
ENV HOST=0.0.0.0
ENV PORT=8000

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
