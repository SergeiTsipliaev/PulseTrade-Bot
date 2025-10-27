from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import asyncio
import logging
import os
import time
from datetime import datetime
import numpy as np
from functools import wraps

# Импорты из проекта
from config import POPULAR_CRYPTOS, CACHE_TTL, DEBUG, SECRET_KEY
from services import bybit_service

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация Flask - ИСПРАВЛЕНО: добавлен ../ для static_folder
app = Flask(__name__, static_folder='../static', static_url_path='')
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


# ======================== МАРШРУТЫ ========================

@app.route('/')
def index():
    """Главная страница"""
    try:
        return send_from_directory(app.static_folder, 'index.html')
    except Exception as e:
        logger.error(f"❌ Ошибка загрузки index.html: {e}")
        return "Error loading app", 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """Проверка здоровья API"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'api': 'Bybit API v5',
        'features': ['search', 'ticker', 'klines', 'indicators', 'predictions']
    }), 200


@app.route('/api/search', methods=['GET'])
@run_async
async def search_cryptocurrencies():
    """Поиск криптовалют"""
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
        # Ищем через Bybit API
        api_results = await bybit_service.search_cryptocurrencies(query)

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


@app.route('/api/cryptos/all', methods=['GET'])
def get_all_cryptocurrencies():
    """Получение всех популярных криптовалют"""
    try:
        # Проверяем кэш
        cache_key = "all_cryptos"
        cached_result = get_cache(cache_key)
        if cached_result:
            return jsonify(cached_result)

        result = {
            'success': True,
            'data': POPULAR_CRYPTOS,
            'total': len(POPULAR_CRYPTOS),
            'source': 'config'
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


@app.route('/api/crypto/<symbol>', methods=['GET'])
@run_async
async def get_crypto_data(symbol: str):
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
        # Получаем текущую цену
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

        prices = history['prices']

        # Рассчитываем индикаторы
        indicators = await bybit_service.calculate_technical_indicators(prices)

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


@app.route('/api/predict/<symbol>', methods=['POST'])
@run_async
async def predict_price(symbol: str):
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

        # Простой линейный прогноз
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


@app.route('/api/klines/<symbol>', methods=['GET'])
@run_async
async def get_klines(symbol: str):
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


# ======================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ========================

def simple_linear_prediction(prices: np.ndarray, days: int = 7) -> np.ndarray:
    """Простой линейный прогноз"""
    try:
        x = np.arange(len(prices))
        y = prices

        coeffs = np.polyfit(x, y, 1)
        poly = np.poly1d(coeffs)

        future_x = np.arange(len(prices), len(prices) + days)
        predictions = poly(future_x)

        predictions = np.maximum(predictions, prices[-1] * 0.5)

        return predictions
    except Exception as e:
        logger.error(f"❌ Ошибка прогноза: {e}")
        return np.array([prices[-1]] * days)


def get_trading_signal(trend: float, prices: np.ndarray) -> tuple:
    """Получить торговый сигнал"""
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
    """Расчет точности прогноза"""
    try:
        if len(predictions) < 1 or len(actual) < 1:
            return 0.0
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


# ======================== ЗАПУСК ========================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"\n{'=' * 70}")
    print(f"🚀 Crypto Tracker (Bybit API)")
    print(f"📊 Адрес: http://localhost:{port}")
    print(f"🔍 Поиск: Да")
    print(f"📈 График: Да")
    print(f"🧠 Прогнозы: Да")
    print(f"{'=' * 70}\n")

    app.run(
        host='0.0.0.0',
        port=port,
        debug=DEBUG,
        threaded=True
    )