# 🚀 Crypto Tracker - Bybit API Edition

Многофункциональный крипто-трекер с поиском, техническим анализом и прогнозами на основе AI.

## 📋 Возможности

- 🔍 **Умный поиск** - поиск по криптовалютам в реальном времени (Bybit API)
- 📊 **Технический анализ** - RSI, Moving Averages, волатильность, тренд
- 🔮 **Прогнозы цен** - линейная регрессия на 7 дней с торговыми сигналами
- 📈 **Интерактивные графики** - Chart.js для визуализации
- 💾 **PostgreSQL кэш** - сохранение популярных криптовалют и истории цен
- 🤖 **Telegram Mini App** - удобный интерфейс прямо в Telegram
- ⚡ **Асинхронные запросы** - быстрая работа с API
- 🐳 **Docker поддержка** - легкое развертывание

## 🛠️ Технологии

- **Backend:** Python, Flask, PostgreSQL, aiohttp
- **Frontend:** Vanilla JavaScript, Chart.js, Telegram Web App SDK
- **API:** Bybit API v5 (публичный, без ключей)
- **Database:** PostgreSQL 15
- **Infrastructure:** Docker, Docker Compose, Nginx

## 🚀 Быстрый старт

### 1. Локальная разработка (без Docker)

#### Требования:
- Python 3.13+
- PostgreSQL 15+
- pip

#### Установка:

```bash
# 1. Клонируйте репозиторий
git clone https://github.com/YOUR_USERNAME/crypto-tracker-bybit.git
cd crypto-tracker-bybit

# 2. Создайте виртуальное окружение
python3.10 -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

# 3. Установите зависимости
pip install --upgrade pip
pip install -r requirements.txt

# 4. Создайте файл .env
cat > .env << EOF
DB_HOST=localhost
DB_PORT=5432
DB_NAME=cryptobot
DB_USER=postgres
DB_PASSWORD=postgres
FLASK_ENV=development
SECRET_KEY=your_secret_key_here
EOF

# 5. Убедитесь что PostgreSQL запущена
brew services start postgresql@15
# Создайте БД:
createdb cryptobot  # Если БД не существует

# 6. Инициализируйте БД
python scripts/init_database.py

# 7. Запустите приложение
python3 -m api.web_app_api
```

Откройте: **http://localhost:5000**

### 2. Docker Compose (рекомендуется)

```bash
# 1. Убедитесь что Docker установлен
docker --version
docker-compose --version

# 2. Запустите контейнеры
docker-compose up -d

# 3. Проверьте статус
docker-compose ps

# 4. Посмотрите логи
docker-compose logs -f api

# 5. Остановите контейнеры
docker-compose down
```

Приложение будет доступно по адресу: **http://localhost:80**

## 📁 Структура проекта

```
crypto-tracker-bybit/
├── api/
│   ├── __init__.py
│   └── web_app_api.py          # Flask API с асинхронными маршрутами
├── models/
│   ├── __init__.py
│   ├── database.py              # PostgreSQL интеграция
│   └── lstm_model.py            # LSTM для прогнозов
├── services/
│   ├── __init__.py
│   └── bybit_service.py         # Асинхронный Bybit API клиент
├── scripts/
│   ├── __init__.py
│   └── init_database.py         # Инициализация БД
├── static/
│   ├── index.html               # Главная страница Mini App
│   └── app.js                   # JavaScript логика
├── config.py                    # Конфигурация приложения
├── requirements.txt             # Python зависимости
├── .env                         # Переменные окружения
├── Dockerfile                   # Контейнеризация
├── docker-compose.yml           # Оркестрация контейнеров
├── nginx.conf                   # Конфигурация Nginx
└── README.md                    # Документация
```

## 🔗 API Endpoints

### Здоровье приложения
```
GET /api/health
Ответ: {status, database, api, features}
```

### Поиск криптовалют
```
GET /api/search?q=bitcoin
Параметры: q - строка поиска (минимум 1 символ)
Ответ: {success, data: [{symbol, name, display_name, emoji}], source}
```

### Все криптовалюты
```
GET /api/cryptos/all
Ответ: {success, data: [crypto], total, source}
```

### Данные криптовалюты
```
GET /api/crypto/BTCUSDT
Ответ: {
    success,
    data: {
        symbol,
        current: {price, change_24h, high_24h, low_24h, volume_24h},
        history: {prices, timestamps},
        indicators: {rsi, ma_7, ma_25, ma_50, volatility, trend_strength}
    }
}
```

### Прогноз цены
```
POST /api/predict/BTCUSDT
Ответ: {
    success,
    data: {
        symbol,
        current_price,
        predictions: [7 дневные значения],
        predicted_change,
        signal: STRONG_BUY|BUY|HOLD|SELL|STRONG_SELL,
        signal_text,
        signal_emoji,
        metrics: {accuracy, rmse}
    }
}
```

### Свечи (Klines)
```
GET /api/klines/BTCUSDT?interval=60&limit=200
Параметры:
  - interval: 1, 5, 15, 60, 240, D, W, M
  - limit: 1-1000 (по умолчанию 200)

Ответ: {
    success,
    data: [{timestamp, open, high, low, close, volume}],
    symbol,
    interval,
    count
}
```

## 📊 Технические индикаторы

**RSI (Relative Strength Index)**
- Период: 14 дней
- Уровни: > 70 (перекупленность), < 30 (перепроданность)

**Moving Averages**
- MA-7: Скользящая средняя за 7 дней
- MA-25: Скользящая средняя за 25 дней
- MA-50: Скользящая средняя за 50 дней

**Волатильность**
- Стандартное отклонение доходности (%)

**Тренд**
- Процентное изменение от первой до последней цены

## 🔮 Система прогнозов

### Алгоритм

1. **Линейная регрессия** на основе 90 дневной истории
2. **Торговые сигналы** на основе тренда и RSI
3. **Метрики** - точность (%) и RMSE (ошибка в USDT)

### Торговые сигналы

| Сигнал | Условие | Emoji |
|--------|---------|-------|
| STRONG_BUY | Тренд > +10% и RSI < 70 | 🟢 |
| BUY | Тренд > +3% и RSI < 70 | 🟢 |
| HOLD | -3% ≤ Тренд ≤ +3% и 30 < RSI < 70 | 🟡 |
| SELL | Тренд < -3% и RSI > 30 | 🔴 |
| STRONG_SELL | Тренд < -10% и RSI > 30 | 🔴 |

## 🔐 Безопасность

✅ **Что реализовано:**
- CORS настроен правильно
- Нет хранения чувствительных данных
- Асинхронные запросы (защита от блокировки)
- SSL/TLS поддержка (certifi)
- Кэширование для снижения нагрузки на API

❌ **Что НЕ используется:**
- API ключи (публичный Bybit API)
- Аутентификация пользователя
- Юридически обязывающие рекомендации

## 🐛 Troubleshooting

### Проблема: БД не подключается

```
Error: PostgreSQL недоступна
```

**Решение:**
```bash
# Проверьте что PostgreSQL запущена
sudo systemctl status postgresql  # Linux
brew services list | grep postgres  # Mac

# Или используйте Docker
docker-compose up postgres -d
```

### Проблема: Port 5000 занят

```
OSError: [Errno 48] Address already in use
```

**Решение:**
```bash
# Найти и убить процесс
lsof -i :5000  # Linux/Mac
netstat -ano | findstr :5000  # Windows

# Или использовать другой порт
PORT=5001 python -m api.web_app_api
```

### Проблема: Импорты не работают

```
ModuleNotFoundError: No module named 'config'
```

**Решение:**
```bash
# Убедитесь что вы в корневой директории проекта
cd /path/to/crypto-tracker-bybit
python -m api.web_app_api  # Используйте -m флаг
```

### Проблема: Асинхронные ошибки

```
RuntimeError: asyncio.run() cannot be called from a running event loop
```

**Решение:** Это известная проблема с Flask и asyncio. Приложение использует `run_async` декоратор для обхода.

## 📈 Performance

- **Latency**: < 500ms для большинства запросов
- **Throughput**: ~ 1000 req/sec на локальной машине
- **Cache TTL**: 5 минут для цен
- **DB Queries**: Индексированы по symbol и timestamp

## 🤖 Интеграция с Telegram

### Создание Mini App

1. Откройте [@BotFather](https://t.me/botfather)
2. `/newbot` - создайте бота
3. `/mybots` -> выберите бота -> Menu Button
4. Установите URL вашего приложения

### Пример settings.json для Telegram

```json
{
    "menu_button": {
        "type": "web_app",
        "text": "📊 Открыть Tracker",
        "web_app": {
            "url": "https://your-domain.com"
        }
    }
}
```

## 📝 Примеры использования API

### JavaScript Fetch

```javascript
// Поиск криптовалют
const searchResponse = await fetch('/api/search?q=bitcoin');
const searchData = await searchResponse.json();

// Получение данных
const cryptoResponse = await fetch('/api/crypto/BTCUSDT');
const cryptoData = await cryptoResponse.json();

// Прогноз
const predictResponse = await fetch('/api/predict/BTCUSDT', {
    method: 'POST'
});
const prediction = await predictResponse.json();
```

## 🚀 Деплой

### ngrok

1. brew install ngrok - установить в корень ноутбука
2. ngrok http 5000


### Render.com

1. Форкните репозиторий на GitHub
2. Создайте аккаунт на [render.com](https://render.com)
3. New -> Web Service
4. Подключите GitHub репозиторий
5. Настройки:
   - Build Command: `pip install -r requirements.txt && python scripts/init_database.py`
   - Start Command: `gunicorn -w 4 -b 0.0.0.0:5000 api.web_app_api:app`
   - Environment: добавьте DATABASE_URL (PostgreSQL на Render)

### Heroku (старый способ)

```bash
# Установите Heroku CLI
# Создайте приложение
heroku create your-app-name

# Добавьте PostgreSQL
heroku addons:create heroku-postgresql:hobby-dev

# Запушьте код
git push heroku main
```

## 📄 Лицензия

MIT License - свободно используйте в личных и коммерческих проектах.

## 👨‍💻 Разработка


### Code Style

Используется PEP 8. Для проверки:

```bash
pip install flake8
flake8 .
```


**Версия:** 2.0.0 (Bybit API Edition)  
**Последнее обновление:** Октябрь 2025