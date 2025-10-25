from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import os
import sys
import ssl
import aiohttp
import asyncio
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

app = Flask(__name__, static_folder='../static')
CORS(app)

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
    return jsonify({'status': 'ok. It`s working'})


@app.route('/api/cryptos', methods=['GET'])
def get_cryptos():
    return jsonify({'success': True, 'data': CRYPTOS})


@app.route('/api/crypto/<crypto_id>', methods=['GET'])
def get_crypto_data(crypto_id):
    print(f"=== GET /api/crypto/{crypto_id} ===")

    try:
        async def fetch_all():
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as session:
                # Current data
                url1 = f"https://api.coingecko.com/api/v3/coins/{crypto_id}"
                params1 = {'localization': 'false', 'tickers': 'false', 'community_data': 'false',
                           'developer_data': 'false'}

                # History
                url2 = f"https://api.coingecko.com/api/v3/coins/{crypto_id}/market_chart"
                params2 = {'vs_currency': 'usd', 'days': 90, 'interval': 'daily'}

                async with session.get(url1, params=params1) as resp1:
                    current = await resp1.json() if resp1.status == 200 else None

                async with session.get(url2, params=params2) as resp2:
                    history = await resp2.json() if resp2.status == 200 else None

                return current, history

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            current_raw, history_raw = loop.run_until_complete(fetch_all())
        finally:
            loop.close()

        if not current_raw or not history_raw:
            return jsonify({'success': False, 'error': 'Failed to fetch data'}), 404

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

        print(f"✅ Success for {crypto_id}")
        return jsonify(
            {'success': True, 'data': {'current': current_data, 'history': history, 'indicators': indicators}})

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/crypto/<crypto_id>', methods=['GET'])
def get_crypto_data(crypto_id):
    print(f"=== GET /api/crypto/{crypto_id} ===")

    try:
        async def fetch_all():
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as session:
                # Current data
                url1 = f"https://api.coingecko.com/api/v3/coins/{crypto_id}"
                params1 = {'localization': 'false', 'tickers': 'false', 'community_data': 'false',
                           'developer_data': 'false'}

                print(f"  📡 Fetching current data from: {url1}")

                # History
                url2 = f"https://api.coingecko.com/api/v3/coins/{crypto_id}/market_chart"
                params2 = {'vs_currency': 'usd', 'days': 90, 'interval': 'daily'}

                print(f"  📡 Fetching history from: {url2}")

                async with session.get(url1, params=params1) as resp1:
                    print(f"  ✅ Current data status: {resp1.status}")
                    current = await resp1.json() if resp1.status == 200 else None

                async with session.get(url2, params=params2) as resp2:
                    print(f"  ✅ History data status: {resp2.status}")
                    history = await resp2.json() if resp2.status == 200 else None

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
            return jsonify({'success': False, 'error': 'Failed to fetch data'}), 404

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

        print(f"✅ Success for {crypto_id}")
        return jsonify(
            {'success': True, 'data': {'current': current_data, 'history': history, 'indicators': indicators}})

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


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))

    # Определяем окружение
    is_production = os.environ.get('ENV') == 'production'

    print(f"\n{'=' * 50}")
    print(f"🚀 Flask app starting on port {port}")
    print(f"🌍 Mode: {'Production' if is_production else 'Development'}")
    print(f"{'=' * 50}")
    print("\n📍 Available routes:")
    for rule in app.url_map.iter_rules():
        methods = ','.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))
        print(f"   {methods:6s} {rule}")
    print(f"\n{'=' * 50}\n")

    if is_production:
        # Production: без debug
        app.run(host='0.0.0.0', port=port, debug=False)
    else:
        # Development: с debug, но с use_reloader=False
        app.run(host='0.0.0.0', port=port, debug=True, use_reloader=False)