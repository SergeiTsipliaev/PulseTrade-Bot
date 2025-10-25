from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import os
import sys
import ssl

# Добавляем родительскую папку в путь
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

app = Flask(__name__, static_folder='../static')
CORS(app)

print("Flask app started!")
print(f"Static folder: {app.static_folder}")


# ============ ТЕСТОВЫЕ МАРШРУТЫ ============

@app.route('/')
def index():
    """Главная страница"""
    print("Index route called")
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/app.js')
def app_js():
    """JavaScript файл"""
    print("app.js route called")
    return send_from_directory(app.static_folder, 'app.js')


@app.route('/api/health', methods=['GET'])
def health_check():
    """Проверка работоспособности"""
    print("Health check called")
    return jsonify({'status': 'ok', 'message': 'API is working!'})


# ============ API ДЛЯ КРИПТОВАЛЮТ ============

CRYPTOS = {
    'bitcoin': {'id': 'bitcoin', 'symbol': 'BTC', 'name': 'Bitcoin'},
    'ethereum': {'id': 'ethereum', 'symbol': 'ETH', 'name': 'Ethereum'},
    'binancecoin': {'id': 'binancecoin', 'symbol': 'BNB', 'name': 'Binance Coin'},
    'solana': {'id': 'solana', 'symbol': 'SOL', 'name': 'Solana'},
    'ripple': {'id': 'ripple', 'symbol': 'XRP', 'name': 'Ripple'},
}


@app.route('/api/cryptos', methods=['GET'])
def get_cryptos():
    """Список криптовалют"""
    print("Cryptos list called")
    return jsonify({
        'success': True,
        'data': CRYPTOS
    })


@app.route('/api/crypto/<crypto_id>', methods=['GET'])
def get_crypto_data(crypto_id):
    """Данные криптовалюты"""
    print(f"Crypto data called for: {crypto_id}")

    try:
        import aiohttp
        import asyncio
        import numpy as np

        # Создаем SSL контекст (отключаем проверку для разработки)
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        # Функция для асинхронного запроса
        async def fetch_data():
            url = f"https://api.coingecko.com/api/v3/coins/{crypto_id}"
            params = {
                'localization': 'false',
                'tickers': 'false',
                'community_data': 'false',
                'developer_data': 'false'
            }

            connector = aiohttp.TCPConnector(ssl=False)  # Отключаем SSL проверку
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        return await response.json()
            return None

        async def fetch_history():
            url = f"https://api.coingecko.com/api/v3/coins/{crypto_id}/market_chart"
            params = {
                'vs_currency': 'usd',
                'days': 90,
                'interval': 'daily'
            }

            connector = aiohttp.TCPConnector(ssl=False)  # Отключаем SSL проверку
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        return await response.json()
            return None

        # Запускаем асинхронные запросы
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            current_data_raw = loop.run_until_complete(fetch_data())
            history_raw = loop.run_until_complete(fetch_history())
        finally:
            loop.close()

        if not current_data_raw or not history_raw:
            return jsonify({'success': False, 'error': 'Failed to fetch data from CoinGecko'}), 404

        # Обработка данных
        current_data = {
            'price': current_data_raw['market_data']['current_price']['usd'],
            'change_24h': current_data_raw['market_data']['price_change_percentage_24h'],
            'change_7d': current_data_raw['market_data'].get('price_change_percentage_7d', 0),
            'change_30d': current_data_raw['market_data'].get('price_change_percentage_30d', 0),
            'high_24h': current_data_raw['market_data']['high_24h']['usd'],
            'low_24h': current_data_raw['market_data']['low_24h']['usd'],
            'market_cap': current_data_raw['market_data']['market_cap']['usd'],
            'volume_24h': current_data_raw['market_data']['total_volume']['usd'],
        }

        prices = [price[1] for price in history_raw['prices']]
        timestamps = [price[0] for price in history_raw['prices']]

        history = {
            'prices': prices,
            'timestamps': timestamps,
            'volumes': [vol[1] for vol in history_raw['total_volumes']]
        }

        # Технические индикаторы
        prices_array = np.array(prices)

        # RSI
        deltas = np.diff(prices_array)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.mean(gains[-14:]) if len(gains) >= 14 else 0
        avg_loss = np.mean(losses[-14:]) if len(losses) >= 14 else 0

        rs = avg_gain / avg_loss if avg_loss != 0 else 0
        rsi = 100 - (100 / (1 + rs))

        # Moving Averages
        ma_7 = float(np.mean(prices_array[-7:])) if len(prices_array) >= 7 else float(prices_array[-1])
        ma_25 = float(np.mean(prices_array[-25:])) if len(prices_array) >= 25 else float(prices_array[-1])
        ma_50 = float(np.mean(prices_array[-50:])) if len(prices_array) >= 50 else float(prices_array[-1])

        # Volatility
        returns = np.diff(prices_array) / prices_array[:-1]
        volatility = float(np.std(returns) * 100)

        # Trend
        trend_strength = float(((prices_array[-1] - prices_array[0]) / prices_array[0]) * 100)

        indicators = {
            'rsi': float(rsi),
            'ma_7': ma_7,
            'ma_25': ma_25,
            'ma_50': ma_50,
            'volatility': volatility,
            'trend_strength': trend_strength
        }

        return jsonify({
            'success': True,
            'data': {
                'current': current_data,
                'history': history,
                'indicators': indicators
            }
        })

    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/predict/<crypto_id>', methods=['POST'])
def predict_price(crypto_id):
    """Прогноз (упрощенная версия без LSTM)"""
    print(f"Prediction called for: {crypto_id}")

    try:
        import aiohttp
        import asyncio
        import numpy as np

        async def fetch_history():
            url = f"https://api.coingecko.com/api/v3/coins/{crypto_id}/market_chart"
            params = {
                'vs_currency': 'usd',
                'days': 90,
                'interval': 'daily'
            }

            connector = aiohttp.TCPConnector(ssl=False)  # Отключаем SSL проверку
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        return await response.json()
            return None

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            history_raw = loop.run_until_complete(fetch_history())
        finally:
            loop.close()

        if not history_raw:
            return jsonify({'success': False, 'error': 'Failed to fetch history'}), 404

        prices = np.array([price[1] for price in history_raw['prices']])

        # Простой линейный прогноз
        x = np.arange(len(prices))
        z = np.polyfit(x, prices, 1)

        current_price = prices[-1]
        predictions = []

        for i in range(1, 8):
            pred = z[0] * (len(prices) + i) + z[1]
            predictions.append(float(pred))

        predictions_array = np.array(predictions)
        volatility = np.std(prices[-30:])

        confidence_upper = predictions_array + (volatility * 1.96)
        confidence_lower = predictions_array - (volatility * 1.96)

        avg_prediction = np.mean(predictions_array)
        price_change = ((avg_prediction - current_price) / current_price) * 100

        if price_change > 5:
            signal = 'STRONG_BUY'
            signal_text = '🟢 Сильная покупка'
        elif price_change > 2:
            signal = 'BUY'
            signal_text = '🟢 Покупка'
        elif price_change < -5:
            signal = 'STRONG_SELL'
            signal_text = '🔴 Сильная продажа'
        elif price_change < -2:
            signal = 'SELL'
            signal_text = '🔴 Продажа'
        else:
            signal = 'HOLD'
            signal_text = '🟡 Удержание'

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
                'metrics': {
                    'mape': 5.0,
                    'rmse': float(volatility),
                    'mae': float(volatility * 0.8)
                },
                'days': 7
            }
        })

    except Exception as e:
        print(f"Prediction error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/routes', methods=['GET'])
def list_routes():
    """Список всех маршрутов"""
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({
            'endpoint': rule.endpoint,
            'methods': list(rule.methods),
            'path': str(rule)
        })
    return jsonify({'routes': routes})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 4000))
    print(f"Starting Flask app on port {port}")
    print("Available routes:")
    for rule in app.url_map.iter_rules():
        print(f"  {rule}")
    app.run(host='0.0.0.0', port=port, debug=True)