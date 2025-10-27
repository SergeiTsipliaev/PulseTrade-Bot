FROM python:3.13-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Копирование requirements
COPY requirements.txt .

# Установка Python зависимостей
RUN pip3 install --no-cache-dir -r requirements.txt

# Копирование кода приложения
COPY . .

# Создание необходимых директорий
RUN mkdir -p logs data/models

# Открытие порта
EXPOSE 5000

# Переменные окружения
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# Запуск приложения
CMD ["python", "-m", "api.web_app_api"]