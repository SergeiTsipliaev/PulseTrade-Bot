from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import os
import sys
import asyncio
import aiohttp
import numpy as np
import time
import logging
from datetime import datetime, timedelta

# КРИТИЧЕСКИ ВАЖНО: Добавляем корневую директорию в PYTHONPATH
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
sys.path.insert(0, project_root)

print(f"🔧 PYTHONPATH: {sys.path}")

try:
    from services.coinbase_service import coinbase_service
    from models.database import db

    DB_AVAILABLE = True
    print("✅ Все модули загружены успешно")
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("❌ Проверьте наличие файлов:")
    print("   - services/coinbase_service.py")
    print("   - models/database.py")
    DB_AVAILABLE = False


    # Заглушки для тестирования
    class DatabaseStub:
        def search_cryptocurrencies(self, query): return []

        def add_cryptocurrency(self, *args): return False

        def get_all_cryptocurrencies(self): return []


    db = DatabaseStub()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='../static')
CORS(app)

# Кэш для данных
cache = {}
CACHE_TTL = 60

# Популярные криптовалюты для fallback
POPULAR_CRYPTOS = {
    'BTC': {'symbol': 'BTC', 'name': 'Bitcoin'},
    'ETH': {'symbol': 'ETH', 'name': 'Ethereum'},
    'BNB': {'symbol': 'BNB', 'name': 'Binance Coin'},
    'SOL': {'symbol': 'SOL', 'name': 'Solana'},
    'XRP': {'symbol': 'XRP', 'name': 'Ripple'},
    'ADA': {'symbol': 'ADA', 'name': 'Cardano'},
    'DOGE': {'symbol': 'DOGE', 'name': 'Dogecoin'},
}


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
        'api': 'Coinbase API',
        'database': 'available' if DB_AVAILABLE else 'unavailable',
        'features': ['поиск', 'прогнозы', 'все криптовалюты'],
        'timestamp': datetime.now().isoformat()
    })


# 🔍 ПОИСК КРИПТОВАЛЮТ
@app.route('/api/search', methods=['GET'])
def search_cryptocurrencies():
    query = request.args.get('q', '').strip()

    if not query or len(query) < 1:
        return jsonify({'success': True, 'data': []})

    logger.info(f"🔍 Поиск: '{query}'")

    try:
        # Сначала ищем в БД (если доступна)
        if DB_AVAILABLE:
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
                logger.info(f"✅ Найдено в БД: {len(results)} результатов")
                return jsonify({'success': True, 'data': results, 'source': 'database'})

        # Ищем через Coinbase API
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

        logger.info(f"✅ Найдено через API: {len(results)} результатов")
        return jsonify({'success': True, 'data': results, 'source': 'coinbase'})

    except Exception as e:
        logger.error(f"❌ Ошибка поиска: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# 📊 ВСЕ КРИПТОВАЛЮТЫ
@app.route('/api/cryptos/all', methods=['GET'])
def get_all_cryptocurrencies():
    try:
        if DB_AVAILABLE:
            cryptocurrencies = db.get_all_cryptocurrencies()
            results = [
                {
                    'id': row['coinbase_id'],
                    'symbol': row['symbol'],
                    'name': row['name']
                }
                for row in cryptocurrencies
            ]
            source = 'database'
        else:
            # Fallback: возвращаем популярные криптовалюты
            results = [
                {
                    'id': crypto_id,
                    'symbol': data['symbol'],
                    'name': data['name']
                }
                for crypto_id, data in POPULAR_CRYPTOS.items()
            ]
            source = 'fallback'

        logger.info(f"📋 Загружено {len(results)} криптовалют ({source})")
        return jsonify({
            'success': True,
            'data': results,
            'total': len(results),
            'source': source
        })

    except Exception as e:
        logger.error(f"❌ Ошибка получения списка: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# 💰 ДАННЫЕ КРИПТОВАЛЮТЫ
@app.route('/api/crypto/<crypto_id>', methods=['GET'])
def get_crypto_data(crypto_id):
    logger.info(f"📊 GET /api/crypto/{crypto_id}")

    # Проверка кэша
    if crypto_id in cache:
        cached_data, cached_time = cache[crypto_id]
        age = time.time() - cached_time
        if age < CACHE_TTL:
            logger.info(f"💾 Кэш ({int(age)}с)")
            return jsonify(cached_data)

    try:
        # Получаем текущую цену асинхронно
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            price_data = loop.run_until_complete(
                coinbase_service.get_currency_price(crypto_id)
            )
        finally:
            loop.close()

        if not price_data:
            logger.warning(f"⚠️ Не удалось получить данные для {crypto_id}")
            return jsonify({
                'success': False,
                'error': f'Не удалось получить данные для {crypto_id}'
            }), 500

        current_price = price_data['price']

        # Генерируем демо-данные
        prices = generate_sample_data(current_price)
        timestamps = generate_timestamps()

        # Расчет индикаторов
        indicators = calculate_indicators(prices)

        result = {
            'success': True,
            'data': {
                'id': crypto_id,
                'symbol': crypto_id,
                'name': crypto_id,
                'current': {
                    'price': current_price,
                    'currency': price_data['currency'],
                    'base': price_data['base'],
                    'pair': price_data.get('pair', 'N/A'),
                    'change_24h': 0,
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

        logger.info(f"✅ Успех: {crypto_id} - ${current_price:,.2f}")
        return jsonify(result)

    except Exception as e:
        logger.error(f"❌ Ошибка получения данных: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# 🔮 ПРОГНОЗ
@app.route('/api/predict/<crypto_id>', methods=['POST'])
def predict_price(crypto_id):
    logger.info(f"🔮 Прогноз для: {crypto_id}")

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

        # Простой прогноз
        predictions = simple_prediction(current_price)

        logger.info(f"✅ Прогноз создан для {crypto_id}")

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
        logger.error(f"❌ Ошибка прогноза: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# 🛠️ ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
def generate_sample_data(current_price):
    """Генерация демо-данных"""
    np.random.seed(42)
    prices = [current_price]
    for i in range(89):
        change = np.random.normal(0, 0.02)
        new_price = max(prices[-1] * (1 + change), 0.01)
        prices.append(new_price)
    return prices


def generate_timestamps():
    """Генерация временных меток"""
    now = datetime.now()
    return [(now - timedelta(days=89 - i)).timestamp() * 1000 for i in range(90)]


def calculate_indicators(prices):
    """Расчет технических индикаторов"""
    try:
        prices_array = np.array(prices)

        # RSI
        if len(prices_array) > 1:
            deltas = np.diff(prices_array)
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)

            avg_gain = np.mean(gains[-14:]) if len(gains) >= 14 else 0
            avg_loss = np.mean(losses[-14:]) if len(losses) >= 14 else 0
            rs = avg_gain / avg_loss if avg_loss != 0 else 0
            rsi = 100 - (100 / (1 + rs))
        else:
            rsi = 50.0

        # Moving Averages
        ma_7 = float(np.mean(prices_array[-7:])) if len(prices_array) >= 7 else float(prices_array[-1])
        ma_25 = float(np.mean(prices_array[-25:])) if len(prices_array) >= 25 else ma_7

        # Volatility
        if len(prices_array) > 1:
            returns = np.diff(prices_array) / prices_array[:-1]
            volatility = float(np.std(returns) * 100) if len(returns) > 0 else 0
        else:
            volatility = 0

        return {
            'rsi': float(rsi),
            'ma_7': ma_7,
            'ma_25': ma_25,
            'volatility': volatility
        }
    except Exception as e:
        logger.error(f"❌ Ошибка расчета индикаторов: {e}")
        return {
            'rsi': 50.0,
            'ma_7': prices[-1] if prices else 0,
            'ma_25': prices[-1] if prices else 0,
            'volatility': 0
        }


def simple_prediction(current_price):
    """Простой прогноз цен"""
    return [current_price * (1 + 0.01 * i) for i in range(1, 8)]


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"\n{'=' * 60}")
    print(f"🚀 Crypto Tracker с поиском")
    print(f"📊 База данных: {'доступна' if DB_AVAILABLE else 'недоступна'}")
    print(f"🔍 Поиск: Coinbase API")
    print(f"⚡ Асинхронные запросы: aiohttp")
    print(f"{'=' * 60}")
    app.run(host='0.0.0.0', port=port, debug=False)