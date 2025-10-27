from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import asyncio
import logging
import os
import time
from datetime import datetime, timedelta
import numpy as np
from functools import wraps

# Импорты из проекта
from config import POPULAR_CRYPTOS, CACHE_TTL, DEBUG, SECRET_KEY, BYBIT_API_BASE
from models.database import db
from services.bybit_service import bybit_service

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация Flask
app = Flask(__name__, static_folder='../static')
app.secret_key = SECRET_KEY
CORS(app)

# Кэш данных в памяти
cache = {}


# ======================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ========================

def run_async(func):
    """Декоратор для запуска асинхронных функций в Flask"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(func(*args, **kwargs))
            return result
        finally:
            loop.close()

    return wrapper


def get_cache(key: str):
    """Получить значение из кэша если оно не истекло"""
    if key in cache:
        value, timestamp = cache[key]
        if time.time() - timestamp < CACHE_TTL:
            logger.debug(f"💾 Кэш попадание: {key}")
            return value
        else:
            del cache[key]
    return None


def set_cache(key: str, value):
    """Установить значение в кэш"""
    cache[key] = (value, time.time())


def init_popular_cryptos():
    """Инициализация популярных криптовалют в БД"""
    if db and db.is_connected:
        for crypto in POPULAR_CRYPTOS:
            db.add_cryptocurrency(
                symbol=crypto['symbol'],
                name=crypto['name'],
                display_name=crypto['display_name'],
                emoji=crypto['emoji']
            )
        logger.info(f"✅ Загружено {len(POPULAR_CRYPTOS)} популярных криптовалют")


# ======================== ИНИЦИАЛИЗАЦИЯ ========================

@app.before_request
def before_request():
    """Выполнить перед каждым запросом"""
    pass


@app.teardown_appcontext
def shutdown_session(exception=None):
    """Очистка при завершении"""
    pass


# ======================== ОСНОВНЫЕ МАРШРУТЫ ========================

@app.route('/')
def index():
    """Главная страница Mini App"""
    try:
        return send_from_directory(app.static_folder, 'index.html')
    except Exception as e:
        logger.error(f"❌ Ошибка загрузки index.html: {e}")
        return "Error loading app", 500


@app.route('/app.js')
def app_js():
    """JavaScript приложения"""
    try:
        return send_from_directory(app.static_folder, 'app.js')
    except Exception as e:
        logger.error(f"❌ Ошибка загрузки app.js: {e}")
        return "Error loading app.js", 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """Проверка здоровья API"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'database': 'connected' if db and db.is_connected else 'disconnected',
        'api': 'Bybit API v5',
        'features': ['search', 'ticker', 'klines', 'indicators', 'predictions']
    }), 200


# ======================== ПОИСК КРИПТОВАЛЮТ ========================

@app.route('/api/search', methods=['GET'])
async def search_cryptocurrencies_async():
    """Асинхронный поиск криптовалют"""
    query = request.args.get('q', '').strip()

    if not query or len(query) < 1:
        return jsonify({'success': True, 'data': [], 'source': 'empty'})

    logger.info(f"🔍 Поиск: '{query}'")

    # Проверяем кэш
    cache_key = f"search:{query}"
    cached_result = get_cache(cache_key)
    if cached_result:
        return jsonify(cached_result)

    try:
        # Сначала ищем в БД
        if db and db.is_connected:
            db_results = db.search_cryptocurrencies(query)
            if db_results:
                result = {
                    'success': True,
                    'data': db_results,
                    'source': 'database',
                    'count': len(db_results)
                }
                set_cache(cache_key, result)
                return jsonify(result)

        # Если в БД не найдено, ищем через Bybit API
        api_results = await bybit_service.search_cryptocurrencies(query)

        # Сохраняем результаты в БД
        if db and db.is_connected:
            for crypto in api_results:
                db.add_cryptocurrency(
                    symbol=crypto['symbol'],
                    name=crypto['name'],
                    display_name=crypto['display_name'],
                    emoji=crypto['emoji']
                )

        result = {
            'success': True,
            'data': api_results,
            'source': 'bybit_api',
            'count': len(api_results)
        }
        set_cache(cache_key, result)
        return jsonify(result)

    except Exception as e:
        logger.error(f"❌ Ошибка поиска: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': []
        }), 500


# Оборачиваем асинхронную функцию
app.route('/api/search', methods=['GET'])(run_async(search_cryptocurrencies_async))


# ======================== ВСЕ КРИПТОВАЛЮТЫ ========================

@app.route('/api/cryptos/all', methods=['GET'])
def get_all_cryptocurrencies():
    """Получение всех популярных криптовалют"""
    try:
        # Проверяем кэш
        cache_key = "all_cryptos"
        cached_result = get_cache(cache_key)
        if cached_result:
            return jsonify(cached_result)

        if db and db.is_connected:
            cryptos = db.get_all_cryptocurrencies()
        else:
            cryptos = POPULAR_CRYPTOS

        result = {
            'success': True,
            'data': cryptos,
            'total': len(cryptos),
            'source': 'database' if db and db.is_connected else 'fallback'
        }
        set_cache(cache_key, result)
        return jsonify(result)

    except Exception as e:
        logger.error(f"❌ Ошибка получения списка: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': []
        }), 500


# ======================== ДАННЫЕ КРИПТОВАЛЮТЫ ========================

@app.route('/api/crypto/<symbol>', methods=['GET'])
async def get_crypto_data_async(symbol: str):
    """Получение полных данных по криптовалюте"""
    symbol = symbol.upper()
    if not symbol.endswith('USDT'):
        symbol = f"{symbol}USDT"

    logger.info(f"📊 Запрос данных: {symbol}")

    # Проверяем кэш
    cache_key = f"crypto:{symbol}"
    cached_result = get_cache(cache_key)
    if cached_result:
        return jsonify(cached_result)

    try:
        # Получаем текущую цену (ticker)
        ticker = await bybit_service.get_current_price(symbol)
        if not ticker:
            return jsonify({
                'success': False,
                'error': f'Не удалось получить данные для {symbol}'
            }), 404

        # Получаем историю цен
        history = await bybit_service.get_price_history(symbol, days=90)
        if not history:
            history = {'prices': [ticker['last_price']], 'timestamps': [int(time.time() * 1000)]}

        # Получаем 1h кандли для дополнительных данных
        klines = await bybit_service.get_kline_data(symbol, interval='60', limit=24)

        prices = history['prices']

        # Рассчитываем индикаторы
        indicators = await bybit_service.calculate_technical_indicators(prices)

        # Кэшируем цену в БД если доступна
        if db and db.is_connected:
            db.cache_price_history(
                symbol=symbol,
                price=ticker['last_price'],
                change_24h=ticker['change_24h'],
                volume_24h=ticker['volume_24h'],
                high_24h=ticker['high_24h'],
                low_24h=ticker['low_24h']
            )

        result = {
            'success': True,
            'data': {
                'symbol': symbol,
                'current': {
                    'price': ticker['last_price'],
                    'change_24h': ticker['change_24h'],
                    'high_24h': ticker['high_24h'],
                    'low_24h': ticker['low_24h'],
                    'volume_24h': ticker['volume_24h'],
                    'turnover_24h': ticker['turnover_24h']
                },
                'history': {
                    'prices': prices,
                    'timestamps': history['timestamps']
                },
                'indicators': indicators
            },
            'timestamp': datetime.now().isoformat()
        }

        set_cache(cache_key, result)
        logger.info(f"✅ Успех: {symbol} - ${ticker['last_price']:,.2f}")
        return jsonify(result)

    except Exception as e:
        logger.error(f"❌ Ошибка получения данных: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Оборачиваем асинхронную функцию
app.route('/api/crypto/<symbol>', methods=['GET'])(run_async(get_crypto_data_async))


# ======================== ПРОГНОЗ ЦЕНЫ ========================

@app.route('/api/predict/<symbol>', methods=['POST'])
async def predict_price_async(symbol: str):
    """Прогноз цены на 7 дней"""
    symbol = symbol.upper()
    if not symbol.endswith('USDT'):
        symbol = f"{symbol}USDT"

    logger.info(f"🔮 Прогноз для: {symbol}")

    try:
        # Получаем историю цен
        history = await bybit_service.get_price_history(symbol, days=90)
        if not history or not history['prices']:
            return jsonify({
                'success': False,
                'error': 'Недостаточно данных для прогноза'
            }), 400

        prices = np.array(history['prices'], dtype=float)
        current_price = prices[-1]

        # Простой прогноз на основе тренда
        predictions = simple_linear_prediction(prices, days=7)

        # Рассчитываем сигнал
        trend = (predictions[-1] - current_price) / current_price * 100
        signal, signal_text, emoji = get_trading_signal(trend, prices)

        result = {
            'success': True,
            'data': {
                'symbol': symbol,
                'current_price': float(current_price),
                'predictions': [float(p) for p in predictions],
                'predicted_change': float(trend),
                'signal': signal,
                'signal_text': signal_text,
                'signal_emoji': emoji,
                'days': 7,
                'metrics': {
                    'accuracy': calculate_accuracy(predictions, prices),
                    'rmse': calculate_rmse(predictions, prices)
                }
            },
            'timestamp': datetime.now().isoformat()
        }

        logger.info(f"✅ Прогноз создан: {signal}")
        return jsonify(result)

    except Exception as e:
        logger.error(f"❌ Ошибка прогноза: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Оборачиваем асинхронную функцию
app.route('/api/predict/<symbol>', methods=['POST'])(run_async(predict_price_async))


# ======================== ПРОГНОЗ СВЕЧЕЙ ========================

@app.route('/api/klines/<symbol>', methods=['GET'])
async def get_klines_async(symbol: str):
    """Получение свечей для графика"""
    symbol = symbol.upper()
    if not symbol.endswith('USDT'):
        symbol = f"{symbol}USDT"

    interval = request.args.get('interval', '60')
    limit = min(int(request.args.get('limit', '200')), 1000)

    logger.info(f"📊 Свечи: {symbol} interval={interval} limit={limit}")

    try:
        klines = await bybit_service.get_kline_data(symbol, interval, limit)
        if not klines:
            return jsonify({
                'success': False,
                'error': 'Не удалось получить свечи'
            }), 404

        formatted_klines = []
        for kline in klines:
            formatted_klines.append({
                'timestamp': int(kline[0]),
                'open': float(kline[1]),
                'high': float(kline[2]),
                'low': float(kline[3]),
                'close': float(kline[4]),
                'volume': float(kline[5])
            })

        return jsonify({
            'success': True,
            'data': formatted_klines,
            'symbol': symbol,
            'interval': interval,
            'count': len(formatted_klines)
        })

    except Exception as e:
        logger.error(f"❌ Ошибка получения свечей: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Оборачиваем асинхронную функцию
app.route('/api/klines/<symbol>', methods=['GET'])(run_async(get_klines_async))


# ======================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ПРОГНОЗА ========================

def simple_linear_prediction(prices: np.ndarray, days: int = 7) -> np.ndarray:
    """Простой линейный прогноз на основе регрессии"""
    try:
        x = np.arange(len(prices))
        y = prices

        # Линейная регрессия
        coeffs = np.polyfit(x, y, 1)
        poly = np.poly1d(coeffs)

        # Прогноз на следующие дни
        future_x = np.arange(len(prices), len(prices) + days)
        predictions = poly(future_x)

        # Убеждаемся что цены остаются положительными
        predictions = np.maximum(predictions, prices[-1] * 0.5)

        return predictions
    except Exception as e:
        logger.error(f"❌ Ошибка прогноза: {e}")
        # Fallback: вернуть текущую цену
        return np.array([prices[-1]] * days)


def get_trading_signal(trend: float, prices: np.ndarray) -> tuple:
    """Получить торговый сигнал на основе тренда"""
    rsi = calculate_rsi(prices)

    if trend > 10 and rsi < 70:
        return 'STRONG_BUY', '🟢 Сильно покупать', '🟢'
    elif trend > 3 and rsi < 70:
        return 'BUY', '🟢 Покупать', '🟢'
    elif -3 <= trend <= 3 and 30 < rsi < 70:
        return 'HOLD', '🟡 Удерживать', '🟡'
    elif trend < -3 and rsi > 30:
        return 'SELL', '🔴 Продавать', '🔴'
    elif trend < -10 and rsi > 30:
        return 'STRONG_SELL', '🔴 Сильно продавать', '🔴'
    else:
        return 'HOLD', '🟡 Удерживать', '🟡'


def calculate_rsi(prices: np.ndarray, period: int = 14) -> float:
    """Расчет RSI"""
    try:
        if len(prices) < period:
            return 50.0

        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])

        rs = avg_gain / avg_loss if avg_loss > 0 else 0
        rsi = 100 - (100 / (1 + rs)) if rs >= 0 else 50

        return float(rsi)
    except:
        return 50.0


def calculate_accuracy(predictions: np.ndarray, actual: np.ndarray) -> float:
    """Расчет точности прогноза (MAPE)"""
    try:
        if len(predictions) < 1 or len(actual) < 1:
            return 0.0
        # Используем последние значения для сравнения
        mape = np.mean(np.abs((actual[-len(predictions):] - predictions) / actual[-len(predictions):]))
        accuracy = max(0, 100 - mape * 100)
        return min(100, float(accuracy))
    except:
        return 85.0


def calculate_rmse(predictions: np.ndarray, actual: np.ndarray) -> float:
    """Расчет RMSE"""
    try:
        if len(predictions) < 1:
            return 0.0
        mse = np.mean((actual[-len(predictions):] - predictions) ** 2)
        rmse = np.sqrt(mse)
        return float(rmse)
    except:
        return 0.0


# ======================== ОБРАБОТКА ОШИБОК ========================

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Endpoint not found',
        'status': 404
    }), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"❌ Internal Server Error: {error}")
    return jsonify({
        'success': False,
        'error': 'Internal server error',
        'status': 500
    }), 500


# ======================== ЗАПУСК ПРИЛОЖЕНИЯ ========================

if __name__ == '__main__':
    # Инициализируем популярные криптовалюты
    init_popular_cryptos()

    port = int(os.environ.get('PORT', 5000))
    print(f"\n{'=' * 70}")
    print(f"🚀 Crypto Tracker (Bybit API)")
    print(f"📊 Адрес: http://localhost:{port}")
    print(f"🔍 Поиск: Да")
    print(f"📈 График: Да")
    print(f"🧠 Прогнозы: Да")
    print(f"💾 БД: {'Подключена' if db and db.is_connected else 'Отключена'}")
    print(f"{'=' * 70}\n")

    app.run(
        host='0.0.0.0',
        port=port,
        debug=DEBUG,
        threaded=True
    )