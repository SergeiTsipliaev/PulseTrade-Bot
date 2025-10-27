# 🚀 ИНСТРУКЦИЯ ПО УСТАНОВКЕ И ЗАПУСКУ

## 📋 Оглавление

1. [Требования](#требования)
2. [Быстрый старт (Docker)](#быстрый-старт-docker)
3. [Локальная установка](#локальная-установка)
4. [Проверка работоспособности](#проверка-работоспособности)
5. [Часто задаваемые вопросы](#часто-задаваемые-вопросы)

---

## 📦 Требования

### Для Docker (рекомендуется):
- Docker 20.10+
- Docker Compose 1.29+
- 2GB RAM минимум

### Для локальной установки:
- Python 3.10 или выше
- PostgreSQL 15+
- pip (идет с Python)
- 1GB RAM минимум

---

## 🐳 Быстрый старт (Docker)

### Шаг 1: Подготовка

```bash
# Распакуйте архив
unzip crypto-tracker-bybit.zip
cd crypto-tracker-bybit

# Проверьте что Docker установлен
docker --version
docker-compose --version
```

### Шаг 2: Запуск приложения

```bash
# Запустите контейнеры (будет автоматически инициализирована БД)
docker-compose up -d
```

**Ожидаемый вывод:**
```
Creating cryptobot-postgres ... done
Creating cryptobot-api      ... done
Creating cryptobot-nginx    ... done
```

### Шаг 3: Проверка статуса

```bash
# Посмотрите статус контейнеров
docker-compose ps

# Должны быть все 3 контейнера в состоянии "Up"
```

### Шаг 4: Откройте приложение

Откройте в браузере: **http://localhost**

**Вы должны увидеть:**
- ✅ Строка поиска
- ✅ 6 популярных криптовалют (BTC, ETH, BNB, SOL, XRP, ADA)
- ✅ При клике на криптовалюту должна загружаться информация

### Шаг 5: Остановка приложения

```bash
# Остановите контейнеры (данные БД сохраняются)
docker-compose down

# Для полной очистки (удалит БД):
docker-compose down -v
```

---

## 💻 Локальная установка

### Шаг 1: Установка зависимостей

#### На macOS:

```bash
# 1. Установите Homebrew (если не установлен)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. Установите PostgreSQL
brew install postgresql@15

# 3. Запустите PostgreSQL
brew services start postgresql@15

# 4. Проверьте установку
psql --version
```

### Шаг 2: Создание БД

```bash
# Создайте БД cryptobot
createdb -U postgres pulsetrader

# Или через psql:
psql -U postgres
# В psql введите:
# CREATE DATABASE cryptobot;
# \q  (для выхода)
```

### Шаг 3: Подготовка Python окружения

```bash
# 1. Перейдите в директорию проекта
cd /путь/к/crypto-tracker-bybit

# 2. Создайте виртуальное окружение
python3.10 -m venv venv

# 3. Активируйте окружение

# На Windows:
venv\Scripts\activate

# На macOS/Linux:
source venv/bin/activate

# Вы должны увидеть (venv) в начале строки
```

### Шаг 4: Установка зависимостей Python

```bash
# Обновите pip
pip install --upgrade pip

# Установите зависимости
pip install -r requirements.txt

# Проверьте установку (должны быть зеленые ✓)
pip list | grep -E "Flask|psycopg2|aiohttp|numpy"
```

### Шаг 5: Конфигурация переменных окружения

```bash
# Проверьте файл .env
# Он должен содержать:
cat .env

# Пример содержимого:
# DB_HOST=localhost
# DB_PORT=5432
# DB_NAME=cryptobot
# DB_USER=postgres
# DB_PASSWORD=postgres
# FLASK_ENV=development
```

### Шаг 6: Инициализация БД

```bash
# Запустите скрипт инициализации
python scripts/init_database.py

# Вы должны увидеть:
# ✅ Подключение к БД установлено
# ✅ BTCUSDT - Bitcoin ₿
# ✅ ETHUSDT - Ethereum Ξ
# ... (остальные криптовалюты)
# ✅ ИНИЦИАЛИЗАЦИЯ УСПЕШНО ЗАВЕРШЕНА
```

### Шаг 7: Запуск приложения

```bash
# Запустите приложение
python -m api.web_app_api

# Вы должны увидеть:
# ======================================================================
# 🚀 Crypto Tracker (Bybit API)
# 📊 Адрес: http://localhost:5000
# 🔍 Поиск: Да
# ... 
# ======================================================================
```

### Шаг 8: Откройте в браузере

Откройте: **http://localhost:5000**

---

## ✅ Проверка работоспособности

### Проверка 1: Все ли контейнеры запущены? (Docker)

```bash
docker-compose ps

# Вывод должен быть:
# NAME                COMMAND             STATE
# cryptobot-postgres  "docker-entrypoint" Up
# cryptobot-api       "python -m api..."  Up
# cryptobot-nginx     "nginx -g daemon"   Up
```

### Проверка 2: Является ли приложение доступным?

```bash
# Откройте в браузере или используйте curl:
curl http://localhost/api/health

# Ожидаемый ответ:
# {
#   "status": "ok",
#   "database": "connected",
#   "api": "Bybit API v5",
#   "features": [...]
# }
```

### Проверка 3: Работает ли поиск?

```bash
curl "http://localhost/api/search?q=bitcoin"

# Ожидаемый ответ:
# {
#   "success": true,
#   "data": [
#     {"symbol": "BTCUSDT", "name": "Bitcoin", ...},
#     ...
#   ],
#   "count": ...
# }
```

### Проверка 4: Работает ли получение данных?

```bash
curl http://localhost/api/crypto/BTCUSDT

# Ожидаемый ответ:
# {
#   "success": true,
#   "data": {
#     "symbol": "BTCUSDT",
#     "current": {
#       "price": 42000.50,
#       "change_24h": 2.5,
#       ...
#     },
#     ...
#   }
# }
```

---

## ❓ Часто задаваемые вопросы

### Q1: Как остановить и перезапустить приложение?

**Docker:**
```bash
# Остановить
docker-compose stop

# Перезапустить
docker-compose up -d

# Перестроить образы и перезапустить
docker-compose up -d --build
```

**Локально:**
```bash
# Нажмите Ctrl+C в терминале
# Для перезапуска просто запустите снова:
python -m api.web_app_api
```

### Q2: Как просмотреть логи?

**Docker:**
```bash
# Логи API
docker-compose logs -f api

# Логи БД
docker-compose logs -f postgres

# Логи Nginx
docker-compose logs -f nginx

# Все логи
docker-compose logs -f
```

**Локально:**
```bash
# Логи выводятся прямо в консоль
# Или откройте файл logs/app.log
cat logs/app.log
```

### Q3: Порт 5000 или 80 уже используется?

**Docker:**
Измените порт в docker-compose.yml:
```yaml
ports:
  - "8080:5000"  # Используйте 8080 вместо 80
```

**Локально:**
```bash
# Установите другой порт
PORT=5001 python -m api.web_app_api
```

### Q4: Как сбросить БД и начать заново?

**Docker:**
```bash
# Удалите том с БД
docker-compose down -v

# Запустите снова (БД будет пересоздана)
docker-compose up -d
```

**Локально:**
```bash
# Удалите все данные БД
dropdb -U postgres cryptobot

# Создайте БД заново
createdb -U postgres cryptobot

# Инициализируйте
python scripts/init_database.py
```

### Q5: БД не подключается (PostgreSQL недоступна)

**Решение:**

Убедитесь что PostgreSQL запущена:

**Windows:**
```bash
# Проверьте в "Services" (services.msc) что postgresql запущена
# Или перезапустите:
net stop postgresql-x64-15
net start postgresql-x64-15
```

**macOS:**
```bash
# Проверьте статус
brew services list | grep postgres

# Если остановлена, запустите
brew services start postgresql@15
```

**Linux:**
```bash
sudo systemctl status postgresql
sudo systemctl start postgresql
```

**Docker:**
```bash
# Проверьте что контейнер postgres запущен
docker-compose ps postgres

# Если нет, перезапустите
docker-compose up -d postgres
```

### Q6: Как подключиться к БД напрямую?

**Через psql:**
```bash
psql -U postgres -d cryptobot -h localhost -p 5432
```

**Docker:**
```bash
docker-compose exec postgres psql -U postgres -d cryptobot
```

**Через UI (pgAdmin):**
```bash
# Установите pgAdmin
docker run -p 5050:80 dpage/pgadmin4

# Откройте http://localhost:5050
# Email: admin@admin.com
# Password: admin
# Добавьте подключение:
#   Host: postgres (или localhost)
#   Port: 5432
#   Database: cryptobot
#   Username: postgres
#   Password: postgres
```

### Q7: Как отправить изменения на GitHub?

```bash
git add .
git commit -m "Описание изменений"
git push origin main
```

### Q8: Как задействовать это как Telegram Mini App?

1. Создайте бота через [@BotFather](https://t.me/botfather)
2. Получите токен
3. Запустите приложение на сервере (например Render.com)
4. В BotFather установите Menu Button на ваш URL
5. Откройте бота в Telegram и нажмите кнопку

### Q9: Как развернуть на Render.com?

```bash
# 1. Форкните репозиторий на GitHub
# 2. На render.com создайте Web Service
# 3. Подключите GitHub репозиторий
# 4. Настройки:
#    Build Command: pip install -r requirements.txt && python scripts/init_database.py
#    Start Command: gunicorn -w 4 -b 0.0.0.0:5000 api.web_app_api:app
# 5. Добавьте переменные окружения в Environment
# 6. Создайте PostgreSQL через Render
# 7. Нажмите Deploy
```

---

## 🆘 Что делать если что-то сломалось?

### Шаг 1: Проверьте логи

**Docker:**
```bash
docker-compose logs api | tail -50
```

**Локально:**
```bash
# Смотрите сообщения в консоли
tail -50 logs/app.log
```

### Шаг 2: Перезагрузитесь

**Docker:**
```bash
docker-compose restart
```

**Локально:**
```bash
# Нажмите Ctrl+C и запустите снова
python -m api.web_app_api
```

### Шаг 3: Очистите кэш браузера

```
Ctrl+Shift+Delete (Chrome, Firefox)
Cmd+Shift+Delete (Safari)
Ctrl+H -> Очистить историю (Edge)
```

### Шаг 4: Если ничего не помогло

```bash
# Docker полная переиндексация
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d

# Локально
rm -rf venv
python3.10 -m venv venv
source venv/bin/activate  # или venv\Scripts\activate
pip install -r requirements.txt
python scripts/init_database.py
python -m api.web_app_api
```

---

## 📞 Контакты и поддержка

Если у вас остались вопросы:

1. 📖 Прочитайте README.md
2. 🔍 Посмотрите логи
3. 💬 Создайте Issue на GitHub
4. 📧 Свяжитесь с разработчиком

---

## ✨ Поздравляем!

Вы успешно установили Crypto Tracker с поддержкой Bybit API! 🎉

**Что дальше?**
- 📊 Откройте приложение и попробуйте поиск
- 🔮 Сделайте прогноз цены
- 📈 Изучите технические индикаторы
- 🔗 Интегрируйте с Telegram Mini App

**Удачи в работе с криптовалютами!** 🚀💰