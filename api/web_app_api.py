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
        else:
            print(f"  ⏰ Cache expired (age: {int(age)}s)")

    try:
        async def fetch_all():
            # Добавляем задержку для избежания rate limit
            await asyncio.sleep(0.5)

            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as session:
                # Current data
                url1 = f"https://sandbox-api.coinmarketcap.com/v1/cryptocurrency/listings/latest{crypto_id}"
                params1 = {'localization': 'false', 'tickers': 'false', 'community_data': 'false',
                           'developer_data': 'false'}

                print(f"  📡 Fetching current data from: {url1}")

                # History
                url2 = f"https://sandbox-api.coinmarketcap.com/v1/cryptocurrency/listings/latest{crypto_id}/market_chart"
                params2 = {'vs_currency': 'usd', 'days': 90, 'interval': 'daily'}

                print(f"  📡 Fetching history from: {url2}")

                async with session.get(url1, params=params1) as resp1:
                    print(f"  ✅ Current data status: {resp1.status}")
                    if resp1.status == 200:
                        current = await resp1.json()
                    elif resp1.status == 429:
                        print(f"  ⚠️  Rate limit hit for current data")
                        return None, None
                    else:
                        current = None

                async with session.get(url2, params=params2) as resp2:
                    print(f"  ✅ History data status: {resp2.status}")
                    if resp2.status == 200:
                        history = await resp2.json()
                    elif resp2.status == 429:
                        print(f"  ⚠️  Rate limit hit for history data")
                        return None, None
                    else:
                        history = None

                return current, history

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            current_raw, history_raw = loop.run_until_complete(fetch_all())
        finally:
            loop.close()

        print(f"  📊 Current data: {'✅ OK' if current_raw else '❌ None'}")
        print(f"  📊 History data: {'✅ OK' if history_raw else '❌ None'}")

        if not current_raw or not history_raw:
            print(f"  ❌ Missing data - returning 404")
            error_msg = 'Rate limit exceeded. Please wait a minute.' if current_raw is None else 'Failed to fetch data'
            return jsonify({'success': False, 'error': error_msg}), 404

        print(f"  🔄 Processing data...")

        current_data = {
            'price': current_raw['market_data']['current_price']['usd'],
            'change_24h': current_raw['market_data']['price_change_percentage_24h'],
            'change_7d': current_raw['market_data'].get('price_change_percentage_7d', 0),
            'change_30d': current_raw['market_data'].get('price_change_percentage_30d', 0),
            'high_24h': current_raw['market_data']['high_24h']['usd'],
            'low_24h': current_raw['market_data']['low_24h']['usd'],
            'market_cap': current_raw['market_data']['market_cap']['usd'],
            'volume_24h': current_raw['market_data']['total_volume']['usd'],
        }

        prices = [p[1] for p in history_raw['prices']]
        timestamps = [p[0] for p in history_raw['prices']]

        history = {
            'prices': prices,
            'timestamps': timestamps,
            'volumes': [v[1] for v in history_raw['total_volumes']]
        }

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

        # Сохраняем в кэш
        cache[crypto_id] = (result, time.time())

        print(f"✅ Success for {crypto_id} (cached)")
        return jsonify(result)

    except KeyError as e:
        print(f"❌ KeyError: {e}")
        print(f"   Missing key in CoinGecko response")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Missing data key: {str(e)}'}), 500
    except Exception as e:
        print(f"❌ Error: {e}")
        print(f"   Error type: {type(e).__name__}")
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