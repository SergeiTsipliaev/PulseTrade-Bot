FROM python:3.10-slim

WORKDIR /app

# Копируем requirements
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Порт для Flask
EXPOSE 5000

# Команда запуска (можно переопределить)
CMD ["python", "api/web_app_api.py"]