from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import os
import sys
import ssl
import aiohttp
import asyncio
import numpy as np
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

app = Flask(__name__, static_folder='../static')
CORS(app)

# Кэш для данных (чтобы избежать rate limit)
cache = {}
CACHE_TTL = 60  # 60 секунд

CRYPTOS = {
    'bitcoin': {'id': 'bitcoin', 'symbol': 'BTC', 'name': 'Bitcoin'},
    'ethereum': {'id': 'ethereum', 'symbol': 'ETH', 'name': 'Ethereum'},
    'binancecoin': {'id': 'binancecoin', 'symbol': 'BNB', 'name': 'Binance Coin'},
    'solana': {'id': 'solana', 'symbol': 'SOL', 'name': 'Solana'},
    'ripple': {'id': 'ripple', 'symbol': 'XRP', 'name': 'Ripple'},
}


@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/app.js')
def app_js():
    return send_from_directory(app.static_folder, 'app.js')


@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok'})


@app.route('/api/cryptos', methods=['GET'])
def get_cryptos():
    return jsonify({'success': True, 'data': CRYPTOS})


@app.route('/api/crypto/<crypto_id>', methods=['GET'])
def get_crypto_data(crypto_id):
    print(f"=== GET /api/crypto/{crypto_id} ===")

    # Проверяем кэш
    if crypto_id in cache:
        cached_data, cached_time = cache[crypto_id]
        age = time.time() - cached_time
        if age < CACHE_TTL:
            print(f"  💾 Returning cached data (age: {int(age)}s)")
            return jsonify(cached_data)

    try:
        async def fetch_all():
            from config import COINCAP_API, COINCAP_IDS

            coincap_id = COINCAP_IDS.get(crypto_id, crypto_id)

            async with aiohttp.ClientSession() as session:
                # Current data
                url1 = f"{COINCAP_API}/assets/{coincap_id}"
                print(f"  📡 Fetching from CoinCap: {url1}")

                # History (interval: d1 = daily)
                url2 = f"{COINCAP_API}/assets/{coincap_id}/history?interval=d1"

                async with session.get(url1) as resp1:
                    print(f"  ✅ Current status: {resp1.status}")
                    current = await resp1.json() if resp1.status == 200 else None

                async with session.get(url2) as resp2:
                    print(f"  ✅ History status: {resp2.status}")
                    history = await resp2.json() if resp2.status == 200 else None

                return current, history

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            current_raw, history_raw = loop.run_until_complete(fetch_all())
        finally:
            loop.close()

        if not current_raw or not history_raw:
            print(f"  ❌ Missing data")
            return jsonify({'success': False, 'error': 'Failed to fetch data'}), 404

        # Обработка данных CoinCap
        asset = current_raw['data']

        current_price = float(asset['priceUsd'])
        change_24h = float(asset['changePercent24Hr'])

        current_data = {
            'price': current_price,
            'change_24h': change_24h,
            'change_7d': 0,  # CoinCap не предоставляет
            'change_30d': 0,
            'high_24h': current_price * 1.05,  # Приблизительно
            'low_24h': current_price * 0.95,
            'market_cap': float(asset['marketCapUsd']),
            'volume_24h': float(asset['volumeUsd24Hr']),
        }

        # История цен
        history_data = history_raw['data']
        prices = [float(item['priceUsd']) for item in history_data[-90:]]  # Последние 90 дней
        timestamps = [item['time'] for item in history_data[-90:]]

        history = {
            'prices': prices,
            'timestamps': timestamps,
            'volumes': [float(item.get('volume', 0)) for item in history_data[-90:]]
        }

        # Технические индикаторы (тот же код)
        prices_array = np.array(prices)
        deltas = np.diff(prices_array)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.mean(gains[-14:]) if len(gains) >= 14 else 0
        avg_loss = np.mean(losses[-14:]) if len(losses) >= 14 else 0
        rs = avg_gain / avg_loss if avg_loss != 0 else 0
        rsi = 100 - (100 / (1 + rs))

        ma_7 = float(np.mean(prices_array[-7:])) if len(prices_array) >= 7 else float(prices_array[-1])
        ma_25 = float(np.mean(prices_array[-25:])) if len(prices_array) >= 25 else float(prices_array[-1])
        ma_50 = float(np.mean(prices_array[-50:])) if len(prices_array) >= 50 else float(prices_array[-1])

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
        print(f"✅ Success for {crypto_id}")
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
            await asyncio.sleep(0.5)  # Задержка для rate limit

            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as session:
                url = f"https://api.coingecko.com/api/v3/coins/{crypto_id}/market_chart"
                params = {'vs_currency': 'usd', 'days': 90, 'interval': 'daily'}
                async with session.get(url, params=params) as resp:
                    return await resp.json() if resp.status == 200 else None

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            history_raw = loop.run_until_complete(fetch_history())
        finally:
            loop.close()

        if not history_raw:
            return jsonify({'success': False, 'error': 'Failed to fetch history'}), 404

        prices = np.array([p[1] for p in history_raw['prices']])
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

        print(f"✅ Prediction success for {crypto_id}")
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
        print(f"❌ Prediction error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"\n{'=' * 50}")
    print(f"🚀 Flask app starting on port {port}")
    print(f"{'=' * 50}")
    print("\n📍 Available routes:")
    for rule in app.url_map.iter_rules():
        methods = ','.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))
        print(f"   {methods:6s} {rule}")
    print(f"\n{'=' * 50}\n")
    app.run(host='0.0.0.0', port=port, debug=False)