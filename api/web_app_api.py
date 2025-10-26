from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import os
import sys
import asyncio
import numpy as np
import time
from datetime import datetime, timedelta
from services.coinbase_service import coinbase_service
from models.database import db

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

app = Flask(__name__, static_folder='../static')
CORS(app)

# Кэш для данных
cache = {}
CACHE_TTL = 60


@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/app.js')
def app_js():
    return send_from_directory(app.static_folder, 'app.js')


@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'ok',
        'api': 'Coinbase + PostgreSQL',
        'features': ['поиск', 'прогнозы', 'все криптовалюты']
    })


# 🔍 ПОИСК КРИПТОВАЛЮТ
@app.route('/api/search', methods=['GET'])
def search_cryptocurrencies():
    query = request.args.get('q', '').strip()

    if not query or len(query) < 1:
        return jsonify({'success': True, 'data': []})

    print(f"🔍 Поиск: '{query}'")

    try:
        # Сначала ищем в БД
        db_results = db.search_cryptocurrencies(query)

        if db_results:
            results = [
                {
                    'id': row['coinbase_id'],
                    'symbol': row['symbol'],
                    'name': row['name']
                }
                for row in db_results
            ]
            return jsonify({'success': True, 'data': results, 'source': 'database'})

        # Если в БД нет, ищем через Coinbase API
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            api_results = loop.run_until_complete(
                coinbase_service.search_currencies(query)
            )
        finally:
            loop.close()

        results = [
            {
                'id': currency['code'],
                'symbol': currency['symbol'],
                'name': currency['name']
            }
            for currency in api_results
        ]

        return jsonify({'success': True, 'data': results, 'source': 'coinbase'})

    except Exception as e:
        print(f"❌ Ошибка поиска: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# 📊 ВСЕ КРИПТОВАЛЮТЫ
@app.route('/api/cryptos/all', methods=['GET'])
def get_all_cryptocurrencies():
    try:
        cryptocurrencies = db.get_all_cryptocurrencies()

        results = [
            {
                'id': row['coinbase_id'],
                'symbol': row['symbol'],
                'name': row['name']
            }
            for row in cryptocurrencies
        ]

        return jsonify({
            'success': True,
            'data': results,
            'total': len(results)
        })

    except Exception as e:
        print(f"❌ Ошибка получения списка: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# 💰 ДАННЫЕ КРИПТОВАЛЮТЫ
@app.route('/api/crypto/<crypto_id>', methods=['GET'])
def get_crypto_data(crypto_id):
    print(f"\n{'=' * 60}")
    print(f"📊 GET /api/crypto/{crypto_id}")
    print(f"{'=' * 60}")

    # Проверка кэша
    if crypto_id in cache:
        cached_data, cached_time = cache[crypto_id]
        age = time.time() - cached_time
        if age < CACHE_TTL:
            print(f"💾 Кэш ({int(age)}с)")
            return jsonify(cached_data)

    try:
        # Получаем текущую цену
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            price_data = loop.run_until_complete(
                coinbase_service.get_currency_price(crypto_id)
            )
        finally:
            loop.close()

        if not price_data:
            return jsonify({
                'success': False,
                'error': f'Не удалось получить данные для {crypto_id}'
            }), 500

        current_price = price_data['price']

        # Здесь можно добавить получение исторических данных
        # Для демо используем сгенерированные данные
        prices = self.generate_sample_data(current_price)
        timestamps = self.generate_timestamps()

        # Расчет индикаторов
        indicators = self.calculate_indicators(prices)

        result = {
            'success': True,
            'data': {
                'id': crypto_id,
                'symbol': crypto_id,
                'name': crypto_id,
                'current': {
                    'price': current_price,
                    'currency': price_data['currency'],
                    'change_24h': 0,  # Можно получить из Coinbase
                    'volume_24h': 0
                },
                'history': {
                    'prices': prices,
                    'timestamps': timestamps
                },
                'indicators': indicators
            }
        }

        # Кэширование
        cache[crypto_id] = (result, time.time())

        print(f"✅ Успех: {crypto_id} - ${current_price:,.2f}")
        print(f"{'=' * 60}\n")

        return jsonify(result)

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# 🔮 ПРОГНОЗ
@app.route('/api/predict/<crypto_id>', methods=['POST'])
def predict_price(crypto_id):
    print(f"\n🔮 Прогноз для: {crypto_id}")

    try:
        # Получаем текущую цену для прогноза
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            price_data = loop.run_until_complete(
                coinbase_service.get_currency_price(crypto_id)
            )
        finally:
            loop.close()

        if not price_data:
            return jsonify({'success': False, 'error': 'Не удалось получить цену'}), 500

        current_price = price_data['price']

        # Простой прогноз (можно заменить на LSTM)
        predictions = self.simple_prediction(current_price)

        return jsonify({
            'success': True,
            'data': {
                'predictions': predictions,
                'current_price': current_price,
                'predicted_change': 2.5,
                'signal': 'HOLD',
                'signal_text': '🟡 Удержание',
                'days': 7
            }
        })

    except Exception as e:
        print(f"❌ Ошибка прогноза: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# 🛠️ ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
def generate_sample_data(current_price):
    """Генерация демо-данных"""
    prices = [current_price]
    for i in range(89):
        change = np.random.normal(0, 0.02)  # Случайное изменение ±2%
        new_price = prices[-1] * (1 + change)
        prices.append(new_price)
    return prices


def generate_timestamps():
    """Генерация временных меток"""
    now = datetime.now()
    return [(now - timedelta(days=89 - i)).timestamp() * 1000 for i in range(90)]


def calculate_indicators(prices):
    """Расчет технических индикаторов"""
    prices_array = np.array(prices)

    # RSI
    deltas = np.diff(prices_array)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)

    avg_gain = np.mean(gains[-14:]) if len(gains) >= 14 else 0
    avg_loss = np.mean(losses[-14:]) if len(losses) >= 14 else 0
    rs = avg_gain / avg_loss if avg_loss != 0 else 0
    rsi = 100 - (100 / (1 + rs))

    return {
        'rsi': float(rsi),
        'ma_7': float(np.mean(prices_array[-7:])),
        'ma_25': float(np.mean(prices_array[-25:])),
        'volatility': float(np.std(np.diff(prices_array) / prices_array[:-1]) * 100)
    }


def simple_prediction(current_price):
    """Простой прогноз цен"""
    return [current_price * (1 + 0.01 * i) for i in range(1, 8)]


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"\n{'=' * 60}")
    print(f"🚀 Crypto Tracker с поиском")
    print(f"📊 База данных: PostgreSQL")
    print(f"🔍 Поиск: Coinbase API + локальный кэш")
    print(f"{'=' * 60}")
    app.run(host='0.0.0.0', port=port, debug=False)