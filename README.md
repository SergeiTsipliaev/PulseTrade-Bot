# 🚀 Crypto LSTM Predictor - Telegram Mini App

Telegram мини-приложение для прогнозирования цен криптовалют с использованием LSTM нейронной сети.

## 🎯 Возможности

- 📱 **Web App интерфейс** - полноценное мобильное приложение внутри Telegram
- 🧠 **LSTM нейронная сеть** - глубокое обучение для прогнозирования
- 📊 **Технический анализ** - RSI, Moving Averages, волатильность
- 📈 **Интерактивные графики** - Chart.js для визуализации
- 🎯 **Торговые сигналы** - BUY/SELL/HOLD рекомендации
- 🔮 **Прогноз до 7 дней** - с доверительными интервалами
- 💎 **5 криптовалют** - BTC, ETH, BNB, SOL, XRP

## 🏗️ Архитектура

```
crypto-lstm-predictor/
├── bot/
│   ├── main.py           # Запуск бота
│   └── handlers.py       # Обработчики команд
├── api/
│   └── web_app_api.py    # Flask API для Mini App
├── models/
│   └── lstm_model.py     # LSTM модель
├── services/
│   └── crypto_service.py # Сервис работы с CoinGecko API
├── frontend/
│   ├── index.html        # Mini App интерфейс
│   └── app.js            # JavaScript логика
├── config.py             # Конфигурация
├── requirements.txt      # Зависимости
├── Dockerfile           # Docker образ
└── docker-compose.yml   # Оркестрация контейнеров
```

## 🚀 Быстрый старт

### Тест сайта 
```bash 
 python3 -m api.web_app_api
```


### 1. Создание бота

1. Откройте [@BotFather](https://t.me/botfather) в Telegram
2. Создайте нового бота: `/newbot`
3. Получите токен бота
4. Настройте Mini App:
   ```
   /mybots -> Выберите бота -> Bot Settings -> Menu Button
   Укажите URL вашего Mini App
   ```

### 2. Установка

```bash
# Клонируйте репозиторий
git clone <your-repo>
cd crypto-lstm-predictor

# Создайте .env файл
cp .env.example .env

# Отредактируйте .env
nano .env
```

### 3. Запуск с Docker

```bash
# Сборка и запуск
docker-compose up -d

# Просмотр логов
docker-compose logs -f
```

### 4. Запуск без Docker

```bash
# Установите зависимости
pip install -r requirements.txt

# Запустите API
python api/web_app_api.py &

# Запустите бота
python bot/main.py
```

## 📊 Как работает LSTM модель

### Архитектура нейросети

```python
LSTM(50) -> Dropout(0.2) -> 
LSTM(50) -> Dropout(0.2) -> 
LSTM(50) -> Dropout(0.2) -> 
Dense(25) -> Dense(1)
```

### Процесс прогнозирования

1. **Сбор данных**: 90 дней исторических цен из CoinGecko API
2. **Предобработка**: Нормализация MinMaxScaler (0-1)
3. **Создание последовательностей**: Окно 60 временных шагов
4. **Обучение**: 50 эпох с Early Stopping
5. **Прогноз**: Итеративное предсказание на 7 дней
6. **Постобработка**: Денормализация и расчет доверительных интервалов

### Метрики точности

- **MAPE** (Mean Absolute Percentage Error) - средняя абсолютная процентная ошибка
- **RMSE** (Root Mean Square Error) - среднеквадратичная ошибка
- **MAE** (Mean Absolute Error) - средняя абсолютная ошибка

## 🔧 Конфигурация

### config.py параметры

```python
SEQUENCE_LENGTH = 60    # Длина входной последовательности
PREDICTION_DAYS = 7     # Дней для прогноза
EPOCHS = 50            # Эпох обучения
BATCH_SIZE = 32        # Размер батча
```

## 📱 Mini App функционал

### Экраны

1. **Выбор криптовалюты** - 5 карточек с криптовалютами
2. **Текущие данные** - цена, изменение, объем, капитализация
3. **График истории** - 90 дней исторических данных
4. **Технические индикаторы** - RSI, MA, волатильность
5. **Прогноз LSTM** - график с доверительными интервалами
6. **Торговый сигнал** - BUY/SELL/HOLD рекомендация

### API эндпоинты

```
GET  /api/cryptos              # Список криптовалют
GET  /api/crypto/<id>          # Данные криптовалюты
POST /api/predict/<id>         # LSTM прогноз
GET  /api/health               # Healthcheck
```

## 🎨 Дизайн

- **Telegram Web App API** - интеграция с темой Telegram
- **Tailwind CSS** - адаптивный дизайн
- **Chart.js** - красивые графики
- **Gradient cards** - современный UI

## 🔐 Безопасность

- CORS настроен для вашего домена
- Rate limiting на API запросы
- Валидация входных данных
- Безопасное хранение токенов в .env

## 📈 Производительность

- **Кэширование моделей** - модели хранятся в памяти
- **Асинхронные запросы** - aiohttp для API
- **Батч обработка** - эффективное обучение
- **Early Stopping** - предотвращение переобучения

## 🚀 Деплой на продакшн

### Heroku

```bash
heroku create your-app-name
heroku config:set BOT_TOKEN=your_token
git push heroku main
```

### VPS (Ubuntu)

```bash
# Установите Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Клонируйте и запустите
git clone <your-repo>
cd crypto-lstm-predictor
docker-compose up -d
```

## 📝 Дальнейшее развитие

- [ ] Добавить больше криптовалют
- [ ] Интеграция с биржами (Binance API)
- [ ] Push уведомления о сигналах
- [ ] Портфолио трекер
- [ ] Sentiment анализ из Twitter/Reddit
- [ ] Ансамбль моделей (LSTM + GRU + Transformer)
- [ ] Бэктестинг стратегий
- [ ] Multi-language поддержка

## 🐛 Troubleshooting

**Проблема**: Модель долго обучается
**Решение**: Уменьшите EPOCHS или используйте GPU

**Проблема**: API не отвечает
**Решение**: Проверьте CoinGecko rate limits (50 запросов/минуту)

**Проблема**: Mini App не открывается
**Решение**: Проверьте HTTPS на вашем домене

## 📄 Лицензия

MIT License

## 👨‍💻 Автор

Ваше имя - [@your_username](https://t.me/your_username)

## 🌟 Поддержка

Если проект помог вам, поставьте ⭐ на GitHub!

Донаты:
- BTC: your_address
- ETH: your_address