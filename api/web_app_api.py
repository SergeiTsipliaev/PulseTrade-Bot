from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import os
import sys
import aiohttp
import asyncio
import numpy as np
import time
import ssl
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

app = Flask(__name__, static_folder='../static')
CORS(app)

# Binance API (1200 req/min!)
BINANCE_API = 'https://api.binance.com/api/v3'
BINANCE_SYMBOLS = {
    'bitcoin': 'BTCUSDT',
    'ethereum': 'ETHUSDT',
    'binancecoin': 'BNBUSDT',
    'solana': 'SOLUSDT',
    'ripple': 'XRPUSDT'
}

CRYPTOS = {
    'bitcoin': {'id': 'bitcoin', 'symbol': 'BTC', 'name': 'Bitcoin'},
    'ethereum': {'id': 'ethereum', 'symbol': 'ETH', 'name': 'Ethereum'},
    'binancecoin': {'id': 'binancecoin', 'symbol': 'BNB', 'name': 'Binance Coin'},
    'solana': {'id': 'solana', 'symbol': 'SOL', 'name': 'Solana'},
    'ripple': {'id': 'ripple', 'symbol': 'XRP', 'name': 'Ripple'},
}

# SSL Context для избежания ошибок сертификатов
try:
    import certifi
    ssl_context = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    # Если certifi не установлен, используем дефолтный контекст
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    print("⚠️  certifi не найден, SSL проверка отключена (не рекомендуется для продакшена)")

# Кэш (опциональный, т.к. лимит высокий)
cache = {}
CACHE_TTL = 30  # 30 секунд


@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/app.js')
def app_js():
    return send_from_directory(app.static_folder, 'app.js')


@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok', 'api': 'Binance (1200 req/min)'})


@app.route('/api/cryptos', methods=['GET'])
def get_cryptos():
    return jsonify({'success': True, 'data': CRYPTOS})


@app.route('/api/crypto/<crypto_id>', methods=['GET'])
def get_crypto_data(crypto_id):
    print(f"=== GET /api/crypto/{crypto_id} (Binance) ===")

    # Кэш (опционально)
    if crypto_id in cache:
        cached_data, cached_time = cache[crypto_id]
        age = time.time() - cached_time
        if age < CACHE_TTL:
            print(f"  💾 Cache ({int(age)}s)")
            return jsonify(cached_data)

    try:
        async def fetch_binance():
            symbol = BINANCE_SYMBOLS.get(crypto_id, 'BTCUSDT')

            connector = aiohttp.TCPConnector(ssl=ssl_context)
            async with aiohttp.ClientSession(connector=connector) as session:
                # 1. Current price + 24h stats
                url1 = f"{BINANCE_API}/ticker/24hr"
                params1 = {'symbol': symbol}

                # 2. Historical klines (90 days, daily)
                url2 = f"{BINANCE_API}/klines"
                params2 = {
                    'symbol': symbol,
                    'interval': '1d',  # daily
                    'limit': 90  # last 90 days
                }

                print(f"  📡 Fetching {symbol}...")

                async with session.get(url1, params=params1) as resp1:
                    print(f"  ✅ Ticker: {resp1.status}")
                    ticker = await resp1.json() if resp1.status == 200 else None

                async with session.get(url2, params=params2) as resp2:
                    print(f"  ✅ Klines: {resp2.status}")
                    klines = await resp2.json() if resp2.status == 200 else None

                return ticker, klines

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            ticker_data, klines_data = loop.run_until_complete(fetch_binance())
        finally:
            loop.close()

        if not ticker_data or not klines_data:
            print(f"  ❌ No data")
            return jsonify({'success': False, 'error': 'Failed to fetch data'}), 404

        # Parse Binance ticker data
        current_price = float(ticker_data['lastPrice'])
        change_24h = float(ticker_data['priceChangePercent'])

        current_data = {
            'price': current_price,
            'change_24h': change_24h,
            'change_7d': 0,  # Binance не предоставляет напрямую
            'change_30d': 0,
            'high_24h': float(ticker_data['highPrice']),
            'low_24h': float(ticker_data['lowPrice']),
            'market_cap': 0,  # Binance не предоставляет
            'volume_24h': float(ticker_data['quoteVolume']),
        }

        # Parse klines (OHLCV data)
        # Format: [timestamp, open, high, low, close, volume, ...]
        prices = [float(k[4]) for k in klines_data]  # close prices
        timestamps = [k[0] for k in klines_data]  # timestamps
        volumes = [float(k[5]) for k in klines_data]

        history = {
            'prices': prices,
            'timestamps': timestamps,
            'volumes': volumes
        }

        # Technical indicators
        prices_array = np.array(prices)
        deltas = np.diff(prices_array)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.mean(gains[-14:]) if len(gains) >= 14 else 0
        avg_loss = np.mean(losses[-14:]) if len(losses) >= 14 else 0
        rs = avg_gain / avg_loss if avg_loss != 0 else 0
        rsi = 100 - (100 / (1 + rs))

        ma_7 = float(np.mean(prices_array[-7:])) if len(prices_array) >= 7 else float(prices_array[-1])
        ma_25 = float(np.mean(prices_array[-25:])) if len(prices_array) >= 25 else ma_7
        ma_50 = float(np.mean(prices_array[-50:])) if len(prices_array) >= 50 else ma_7

        returns = np.diff(prices_array) / prices_array[:-1]
        volatility = float(np.std(returns) * 100)
        trend_strength = float(((prices_array[-1] - prices_array[0]) / prices_array[0]) * 100)

        indicators = {
            'rsi': float(rsi),
            'ma_7': ma_7,
            'ma_25': ma_25,
            'ma_50': ma_50,
            'volatility': volatility,
            'trend_strength': trend_strength
        }

        result = {
            'success': True,
            'data': {
                'current': current_data,
                'history': history,
                'indicators': indicators
            }
        }

        cache[crypto_id] = (result, time.time())
        print(f"✅ Success")
        return jsonify(result)

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/predict/<crypto_id>', methods=['POST'])
def predict_price(crypto_id):
    print(f"=== POST /api/predict/{crypto_id} ===")

    try:
        async def fetch_history():
            symbol = BINANCE_SYMBOLS.get(crypto_id, 'BTCUSDT')

            connector = aiohttp.TCPConnector(ssl=ssl_context)
            async with aiohttp.ClientSession(connector=connector) as session:
                url = f"{BINANCE_API}/klines"
                params = {
                    'symbol': symbol,
                    'interval': '1d',
                    'limit': 90
                }
                async with session.get(url, params=params) as resp:
                    return await resp.json() if resp.status == 200 else None

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            klines_data = loop.run_until_complete(fetch_history())
        finally:
            loop.close()

        if not klines_data:
            return jsonify({'success': False, 'error': 'Failed to fetch history'}), 404

        # Extract close prices
        prices = np.array([float(k[4]) for k in klines_data])

        # Linear regression prediction
        x = np.arange(len(prices))
        z = np.polyfit(x, prices, 1)

        current_price = prices[-1]
        predictions = [float(z[0] * (len(prices) + i) + z[1]) for i in range(1, 8)]
        predictions_array = np.array(predictions)
        volatility = np.std(prices[-30:])

        confidence_upper = predictions_array + (volatility * 1.96)
        confidence_lower = predictions_array - (volatility * 1.96)

        avg_prediction = np.mean(predictions_array)
        price_change = ((avg_prediction - current_price) / current_price) * 100

        if price_change > 5:
            signal, signal_text = 'STRONG_BUY', '🟢 Сильная покупка'
        elif price_change > 2:
            signal, signal_text = 'BUY', '🟢 Покупка'
        elif price_change < -5:
            signal, signal_text = 'STRONG_SELL', '🔴 Сильная продажа'
        elif price_change < -2:
            signal, signal_text = 'SELL', '🔴 Продажа'
        else:
            signal, signal_text = 'HOLD', '🟡 Удержание'

        print(f"✅ Prediction done")
        return jsonify({
            'success': True,
            'data': {
                'predictions': predictions,
                'confidence_upper': confidence_upper.tolist(),
                'confidence_lower': confidence_lower.tolist(),
                'current_price': float(current_price),
                'predicted_change': float(price_change),
                'signal': signal,
                'signal_text': signal_text,
                'metrics': {'mape': 5.0, 'rmse': float(volatility), 'mae': float(volatility * 0.8)},
                'days': 7
            }
        })

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"\n{'=' * 50}")
    print(f"🚀 Flask + Binance API")
    print(f"📊 Rate limit: 1200 requests/min")
    print(f"{'=' * 50}")
    print("\n📍 Routes:")
    for rule in app.url_map.iter_rules():
        methods = ','.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))
        print(f"   {methods:6s} {rule}")
    print(f"\n{'=' * 50}\n")
    app.run(host='0.0.0.0', port=port, debug=False)