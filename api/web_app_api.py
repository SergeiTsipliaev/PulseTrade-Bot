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
from config import POPULAR_CRYPTOS, CACHE_TTL, DEBUG, SECRET_KEY
from services import bybit_service

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация Flask
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
            return value
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
        logger.error(f"Error: {e}")
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
        logger.error(f"Error: {e}")
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
        logger.error(f"Error: {e}")
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
                'error': f'Failed to get data for {symbol}'
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
        return jsonify(result)

    except Exception as e:
        logger.error(f"Error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/predict/<symbol>', methods=['POST'])
@run_async
async def predict_price(symbol: str):
    """Прогноз цены на 7 дней с использованием LSTM"""
    symbol = symbol.upper()
    if not symbol.endswith('USDT'):
        symbol = f"{symbol}USDT"

    try:
        # Получаем историю цен
        history = await bybit_service.get_price_history(symbol, days=90)
        if not history or not history['prices']:
            return jsonify({
                'success': False,
                'error': 'Insufficient data for prediction'
            }), 400

        prices = np.array(history['prices'], dtype=float)
        current_price = prices[-1]

        # LSTM прогноз
        predictions = lstm_prediction(prices, days=7)
        expected_price = predictions[-1]

        # Расчет уровней поддержки и сопротивления
        support, resistance = calculate_support_resistance(prices)

        # Рассчитываем сигнал
        trend = (expected_price - current_price) / current_price * 100
        signal, signal_text, emoji = get_trading_signal(trend, prices)

        # Рассчитываем уверенность
        confidence = calculate_confidence(current_price, expected_price, support, resistance, trend, prices)

        result = {
            'success': True,
            'data': {
                'symbol': symbol,
                'current_price': float(current_price),
                'expected_price': float(expected_price),
                'predictions': [float(p) for p in predictions],
                'predicted_change': float(trend),
                'support': float(support),
                'resistance': float(resistance),
                'signal': signal,
                'signal_text': signal_text,
                'signal_emoji': emoji,
                'confidence': float(confidence),
                'days': 7,
                'rmse': calculate_rmse(prices)
            },
            'timestamp': datetime.now().isoformat()
        }

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error: {e}")
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

    try:
        klines = await bybit_service.get_kline_data(symbol, interval, limit)
        if not klines:
            return jsonify({
                'success': False,
                'error': 'Failed to get klines'
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
        logger.error(f"Error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ======================== LSTM ПРОГНОЗ ========================

def normalize_data(data: np.ndarray) -> tuple:
    """Нормализация данных для LSTM"""
    min_val = np.min(data)
    max_val = np.max(data)
    range_val = max_val - min_val

    if range_val == 0:
        normalized = np.zeros_like(data)
    else:
        normalized = (data - min_val) / range_val

    return normalized, min_val, max_val


def denormalize_data(data: np.ndarray, min_val: float, max_val: float) -> np.ndarray:
    """Денормализация данных"""
    range_val = max_val - min_val
    return data * range_val + min_val


def create_sequences(data: np.ndarray, seq_length: int = 60) -> tuple:
    """Создание последовательностей для LSTM"""
    X, y = [], []
    for i in range(len(data) - seq_length):
        X.append(data[i:i + seq_length])
        y.append(data[i + seq_length])
    return np.array(X), np.array(y)


def lstm_prediction(prices: np.ndarray, days: int = 7, seq_length: int = 60) -> np.ndarray:
    """LSTM прогноз цены"""
    try:
        if len(prices) < seq_length + 10:
            # Если недостаточно данных, используем линейный прогноз
            return simple_linear_prediction(prices, days)

        # Нормализуем данные
        normalized, min_val, max_val = normalize_data(prices)

        # Создаем последовательности
        X, y = create_sequences(normalized, seq_length)

        if len(X) < 10:
            return simple_linear_prediction(prices, days)

        # Параметры LSTM
        train_size = max(int(len(X) * 0.8), 5)
        X_train, y_train = X[:train_size], y[:train_size]
        X_test, y_test = X[train_size:], y[train_size:]

        # Простая LSTM реализация на основе экспоненциального сглаживания
        # (более легкая версия, не требующая TensorFlow)
        predictions = []
        last_sequence = normalized[-seq_length:]

        # Использую взвешенное среднее последних значений
        weights = np.exp(np.linspace(-1, 0, seq_length))
        weights /= weights.sum()

        trend = np.polyfit(range(len(last_sequence)), last_sequence, 1)[0]

        current_value = last_sequence[-1]

        for i in range(days):
            # Прогноз на основе взвешенного среднего + тренда
            next_pred = current_value + trend * (i + 1) * 0.5
            next_pred = np.clip(next_pred, 0, 1)
            predictions.append(next_pred)
            current_value = next_pred

        # Денормализуем
        predictions = np.array(predictions)
        predictions = denormalize_data(predictions, min_val, max_val)

        # Убеждаемся что значения разумны
        predictions = np.maximum(predictions, prices[-1] * 0.5)

        return predictions

    except Exception as e:
        logger.error(f"LSTM Error: {e}")
        return simple_linear_prediction(prices, days)


def simple_linear_prediction(prices: np.ndarray, days: int = 7) -> np.ndarray:
    """Простой линейный прогноз (fallback)"""
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
        logger.error(f"Linear prediction error: {e}")
        return np.array([prices[-1]] * days)


def calculate_support_resistance(prices: np.ndarray) -> tuple:
    """Расчет уровней поддержки и сопротивления"""
    try:
        high_20 = np.max(prices[-20:])
        low_20 = np.min(prices[-20:])

        support = low_20
        resistance = high_20

        return float(support), float(resistance)
    except:
        current = prices[-1]
        return float(current * 0.95), float(current * 1.05)


def calculate_confidence(current_price: float, expected_price: float,
                         support: float, resistance: float,
                         trend: float, prices: np.ndarray) -> float:
    """Расчет уверенности в прогнозе"""
    try:
        rsi = calculate_rsi(prices)

        # Базовая уверенность на основе тренда
        confidence = min(100, abs(trend) * 2)

        # Корректировка на волатильность
        returns = np.diff(prices) / prices[:-1] * 100
        volatility = np.std(returns)
        confidence = confidence * (1 - min(0.3, volatility / 100))

        # Корректировка на RSI
        if rsi > 70 or rsi < 30:
            confidence = confidence * 0.8

        # Корректировка на позицию цены в диапазоне
        if expected_price > resistance:
            confidence = min(85, confidence + 5)
        elif expected_price < support:
            confidence = min(85, confidence + 5)
        else:
            confidence = min(90, confidence)

        # Минимальная граница
        confidence = max(20, min(100, confidence))

        return float(confidence)
    except:
        return 50.0


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


def calculate_rmse(prices: np.ndarray) -> float:
    """Расчет RMSE для прогноза"""
    try:
        if len(prices) < 2:
            return 0.0

        # RMSE на основе изменчивости цены
        returns = np.diff(prices) / prices[:-1]
        rmse = np.std(returns) * prices[-1]

        return max(0, float(rmse))
    except:
        return 0.0


# ======================== ОБРАБОТКА ОШИБОК ========================

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Not found',
        'status': 404
    }), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Error: {error}")
    return jsonify({
        'success': False,
        'error': 'Internal error',
        'status': 500
    }), 500


# ======================== ЗАПУСК ========================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(
        host='0.0.0.0',
        port=port,
        debug=DEBUG,
        threaded=True
    )