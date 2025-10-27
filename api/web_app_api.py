from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import asyncio
import logging
import os
import time
from datetime import datetime
import numpy as np
from functools import wraps

from config import POPULAR_CRYPTOS, CACHE_TTL, DEBUG, SECRET_KEY
from services import bybit_service

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='../static', static_url_path='')
app.secret_key = SECRET_KEY
CORS(app)

cache = {}


def run_async(func):
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
    if key in cache:
        value, timestamp = cache[key]
        if time.time() - timestamp < CACHE_TTL:
            return value
    return None


def set_cache(key: str, value):
    cache[key] = (value, time.time())


def calculate_rsi(prices: np.ndarray, period: int = 14) -> float:
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


def simple_linear_prediction(prices: np.ndarray, days: int = 7) -> np.ndarray:
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
        logger.error(f"Error: {e}")
        return np.array([prices[-1]] * days)


def calculate_support_resistance(prices: np.ndarray) -> tuple:
    try:
        high_20 = np.max(prices[-20:])
        low_20 = np.min(prices[-20:])
        support = low_20
        resistance = high_20
        return float(support), float(resistance)
    except:
        current = prices[-1]
        return float(current * 0.95), float(current * 1.05)


def calculate_confidence_and_action(current_price: float, expected_price: float,
                                    support: float, resistance: float,
                                    trend: float, prices: np.ndarray) -> tuple:
    try:
        rsi = calculate_rsi(prices)

        # Базовая уверенность зависит от силы тренда
        confidence = min(100, abs(trend) * 1.5)

        # Корректировка по волатильности (высокая волатильность = меньше уверенности)
        returns = np.diff(prices) / prices[:-1] * 100
        volatility = np.std(returns)
        volatility_factor = 1 - min(0.4, volatility / 50)
        confidence = confidence * volatility_factor

        # Корректировка по RSI (если рынок в экстремуме, уверенность снижается)
        if rsi > 70 or rsi < 30:
            confidence = confidence * 0.7
        elif rsi > 60 or rsi < 40:
            confidence = confidence * 0.85

        # Минимум 15%, максимум 95%
        confidence = max(15, min(95, confidence))

        # Определяем действие отдельно
        if expected_price > resistance:
            action = "BUY"
        elif expected_price < support:
            action = "SELL"
        elif expected_price > current_price * 1.05:
            action = "BUY"
        elif expected_price < current_price * 0.95:
            action = "SELL"
        else:
            action = "HOLD"

        return float(confidence), action
    except:
        return 50.0, "HOLD"


def get_trading_signal(trend: float, prices: np.ndarray) -> tuple:
    rsi = calculate_rsi(prices)
    if trend > 10 and rsi < 70:
        return 'STRONG_BUY', '🟢 Strong Buy', '🟢'
    elif trend > 3 and rsi < 70:
        return 'BUY', '🟢 Buy', '🟢'
    elif -3 <= trend <= 3 and 30 < rsi < 70:
        return 'HOLD', '🟡 Hold', '🟡'
    elif trend < -3 and rsi > 30:
        return 'SELL', '🔴 Sell', '🔴'
    elif trend < -10 and rsi > 30:
        return 'STRONG_SELL', '🔴 Strong Sell', '🔴'
    else:
        return 'HOLD', '🟡 Hold', '🟡'


def calculate_accuracy(predictions: np.ndarray, actual: np.ndarray) -> float:
    try:
        if len(predictions) < 1 or len(actual) < 1:
            return 0.0
        mape = np.mean(np.abs((actual[-len(predictions):] - predictions) / actual[-len(predictions):]))
        accuracy = max(0, 100 - mape * 100)
        return min(100, float(accuracy))
    except:
        return 85.0


def calculate_rmse(predictions: np.ndarray, actual: np.ndarray) -> float:
    try:
        if len(predictions) < 1:
            return 0.0
        mse = np.mean((actual[-len(predictions):] - predictions) ** 2)
        rmse = np.sqrt(mse)
        return float(rmse)
    except:
        return 0.0


@app.route('/')
def index():
    try:
        return send_from_directory(app.static_folder, 'index.html')
    except Exception as e:
        logger.error(f"Error: {e}")
        return "Error loading app", 500


@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'api': 'Bybit API v5',
        'features': ['search', 'ticker', 'klines', 'indicators', 'predictions']
    }), 200


@app.route('/api/search', methods=['GET'])
@run_async
async def search_cryptocurrencies():
    query = request.args.get('q', '').strip()
    if not query or len(query) < 1:
        return jsonify({'success': True, 'data': [], 'source': 'empty'})

    cache_key = f"search:{query}"
    cached_result = get_cache(cache_key)
    if cached_result:
        return jsonify(cached_result)

    try:
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
        return jsonify({'success': False, 'error': str(e), 'data': []}), 500


@app.route('/api/cryptos/all', methods=['GET'])
def get_all_cryptocurrencies():
    try:
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
        return jsonify({'success': False, 'error': str(e), 'data': []}), 500


@app.route('/api/crypto/<symbol>', methods=['GET'])
@run_async
async def get_crypto_data(symbol: str):
    symbol = symbol.upper()
    if not symbol.endswith('USDT'):
        symbol = f"{symbol}USDT"

    cache_key = f"crypto:{symbol}"
    cached_result = get_cache(cache_key)
    if cached_result:
        return jsonify(cached_result)

    try:
        ticker = await bybit_service.get_current_price(symbol)
        if not ticker:
            return jsonify({'success': False, 'error': f'Failed to get data for {symbol}'}), 404

        history = await bybit_service.get_price_history(symbol, days=90)
        if not history:
            history = {'prices': [ticker['last_price']], 'timestamps': [int(time.time() * 1000)]}

        prices = history['prices']
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
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/predict/<symbol>', methods=['POST'])
@run_async
async def predict_price(symbol: str):
    symbol = symbol.upper()
    if not symbol.endswith('USDT'):
        symbol = f"{symbol}USDT"

    try:
        history = await bybit_service.get_price_history(symbol, days=90)
        if not history or not history['prices']:
            return jsonify({'success': False, 'error': 'Insufficient data for prediction'}), 400

        prices = np.array(history['prices'], dtype=float)
        current_price = prices[-1]

        predictions = simple_linear_prediction(prices, days=7)
        expected_price = predictions[-1]

        support, resistance = calculate_support_resistance(prices)

        trend = (expected_price - current_price) / current_price * 100
        signal, signal_text, emoji = get_trading_signal(trend, prices)

        confidence, action = calculate_confidence_and_action(
            current_price, expected_price, support, resistance, trend, prices
        )

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
                'action': action,
                'confidence': float(confidence),
                'days': 7,
                'metrics': {
                    'confidence': float(confidence),
                    'rmse': calculate_rmse(predictions, prices)
                }
            },
            'timestamp': datetime.now().isoformat()
        }

        return jsonify(result)
    except Exception as e:
        logger.error(f"Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/klines/<symbol>', methods=['GET'])
@run_async
async def get_klines(symbol: str):
    symbol = symbol.upper()
    if not symbol.endswith('USDT'):
        symbol = f"{symbol}USDT"

    interval = request.args.get('interval', '60')
    limit = min(int(request.args.get('limit', '200')), 1000)

    try:
        klines = await bybit_service.get_kline_data(symbol, interval, limit)
        if not klines:
            return jsonify({'success': False, 'error': 'Failed to get klines'}), 404

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
        return jsonify({'success': False, 'error': str(e)}), 500


@app.errorhandler(404)
def not_found(error):
    return jsonify({'success': False, 'error': 'Not found', 'status': 404}), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Error: {error}")
    return jsonify({'success': False, 'error': 'Internal error', 'status': 500}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=DEBUG, threaded=True)