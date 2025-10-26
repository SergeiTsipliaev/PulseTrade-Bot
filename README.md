Многофункциональный криптотрекер с поиском, техническим анализом и прогнозами на основе AI.

## 🚀 Возможности

- **🔍 Умный поиск** - поиск по 1000+ криптовалют через Coinbase API
- **📊 Технический анализ** - RSI, Moving Averages, волатильность
- **🔮 AI прогнозы** - LSTM нейросеть для предсказания цен
- **🤖 Telegram бот** - удобный интерфейс через Telegram Web App
- **💾 Локальный кэш** - PostgreSQL для быстрого поиска и хранения данных
- **🐳 Docker поддержка** - легкое развертывание

## 🛠 Технологии

- **Backend**: Python, Flask, PostgreSQL, aiohttp
- **Frontend**: Vanilla JavaScript, Chart.js, Telegram Web App
- **AI**: TensorFlow/LSTM для прогнозов
- **Infrastructure**: Docker, Nginx, GitHub Actions

## 📊 API источники

### Coinbase API
- **Rate Limit:** 10,000 запросов/час
- **SSL:** Работает нативно ✅
- **Бесплатно:** Да
- **Используется для:** Текущие цены (spot, buy, sell)

### CryptoCompare API  
- **Rate Limit:** 100,000 запросов/месяц
- **SSL:** Работает нативно ✅
- **Бесплатно:** Да
- **Используется для:** Исторические данные (90 дней)

## 🚀 Быстрый старт

### Локальная разработка

```bash
# 1. Клонируйте репозиторий
git clone https://github.com/YOUR_USERNAME/PulseTrade-Bot.git
cd PulseTrade-Bot

# 2. Создайте виртуальное окружение (Python 3.10)
python3.10 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# или
.venv\Scripts\activate  # Windows

# 3. Установите зависимости
pip install --upgrade pip
pip install -r requirements.txt

# 4. Запустите приложение
python3 -m api.web_app_api
```

Откройте: `http://localhost:5000`

### Создание Telegram бота

1. Откройте [@BotFather](https://t.me/botfather)
2. Создайте бота: `/newbot`
3. Получите токен
4. Настройте Mini App:
   ```
   /mybots -> Выберите бота -> Bot Settings -> Menu Button
   URL: https://your-app.onrender.com
   ```

### Деплой на Render.com

1. **Форкните** репозиторий на GitHub
2. Зарегистрируйтесь на [Render.com](https://render.com)
3. Создайте **New Web Service**
4. Подключите ваш GitHub репозиторий
5. Настройки:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python api/web_app_api.py`
   - **Instance Type:** Free
6. Нажмите **Create Web Service**

## 📁 Структура проекта

```
PulseTrade-Bot/
├── api/
│   ├── __init__.py
│   └── web_app_api.py       # Flask API (Coinbase + CryptoCompare)
├── bot/
│   ├── __init__.py
│   ├── handlers.py          # Обработчики команд
│   └── main.py              # Запуск бота
├── static/
│   ├── index.html           # Mini App UI
│   └── app.js               # JavaScript логика
├── services/
│   ├── __init__.py
│   └── crypto_service.py    # Сервис работы с API
├── config.py                # Конфигурация
├── requirements.txt         # Зависимости Python
├── runtime.txt              # Python версия (3.10.11)
├── Procfile                 # Команда запуска
└── README.md                # Документация
```

## 🔧 API Эндпоинты

```
GET  /                       # Главная страница Mini App
GET  /api/health             # Проверка статуса
GET  /api/cryptos            # Список криптовалют
GET  /api/crypto/<id>        # Данные криптовалюты
POST /api/predict/<id>       # Прогноз цены
```

### Пример запроса

```bash
# Получить данные Bitcoin
curl http://localhost:5000/api/crypto/bitcoin

# Получить прогноз Ethereum
curl -X POST http://localhost:5000/api/predict/ethereum
```

## 📊 Технический анализ

Приложение рассчитывает следующие индикаторы:

- **RSI (Relative Strength Index)** - индикатор перекупленности/перепроданности
- **MA-7, MA-25, MA-50** - скользящие средние
- **Volatility** - волатильность цены
- **Trend Strength** - сила тренда

## 🔮 Прогнозирование

Использует **линейную регрессию** для прогноза цен на 7 дней вперед:
- Анализирует 90 дней исторических данных
- Рассчитывает доверительные интервалы (±1.96σ)
- Генерирует торговые сигналы (STRONG_BUY/BUY/HOLD/SELL/STRONG_SELL)

## 🎨 Mini App функционал

1. **Выбор криптовалюты** - 5 карточек (BTC, ETH, BNB, SOL, XRP)
2. **Текущие данные** - цена, изменение за 24ч
3. **График истории** - 90 дней с Chart.js
4. **Технические индикаторы** - RSI, MA, волатильность, тренд
5. **Прогноз** - график на 7 дней с доверительными интервалами
6. **Торговый сигнал** - рекомендация BUY/SELL/HOLD

## 🔐 Безопасность

- ✅ CORS настроен
- ✅ Нет API ключей (публичные endpoints)
- ✅ Кэширование (60 сек TTL)
- ✅ SSL работает нативно

## 🐛 Troubleshooting

### Проблема: SSL ошибки

**Решение:** Этот проект использует Coinbase и CryptoCompare, у которых нет проблем с SSL на macOS/Linux.

### Проблема: Rate limit

**Решение:** 
- Coinbase: 10,000 req/hour (очень щедро)
- CryptoCompare: 100,000 req/month
- Приложение использует кэширование (60 сек)

### Проблема: Mini App не открывается

**Решение:**
1. Проверьте HTTPS на вашем домене (Render дает автоматически)
2. Убедитесь, что URL в BotFather правильный
3. Проверьте логи: `https://dashboard.render.com`

## 📝 TODO

- [ ] Добавить больше криптовалют
- [ ] Интеграция с реальной LSTM моделью
- [ ] Push уведомления о сигналах
- [ ] Портфолио трекер
- [ ] Мульти-язык (EN/RU)
- [ ] Темная/светлая тема
- [ ] Настройки пользователя

## 📄 Лицензия

MIT License

## 👨‍💻 Контакты

- GitHub: [@YOUR_USERNAME](https://github.com/YOUR_USERNAME)
- Telegram: [@your_username](https://t.me/your_username)

## 🌟 Поддержка

Если проект помог вам, поставьте ⭐ на GitHub!