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

# КРИТИЧЕСКИ ВАЖНО: Правильно добавляем корневую директорию
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

print(f"🔧 Загрузка модулей из: {project_root}")

try:
    from services.coinbase_service import coinbase_service
    from models.database import db

    DB_AVAILABLE = True
    print("✅ Все модули загружены успешно")
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    import traceback

    traceback.print_exc()
    DB_AVAILABLE = False


    # Заглушки для тестирования
    class DatabaseStub:
        def search_cryptocurrencies(self, query):
            return []

        def add_cryptocurrency(self, *args):
            return False

        def get_all_cryptocurrencies(self):
            return []


    class CoinbaseServiceStub:
        async def search_currencies(self, query):
            return []

        async def get_currency_price(self, currency_id):
            # Возвращаем тестовые данные
            return {
                'price': 45000.0 if currency_id == 'BTC' else 3000.0,
                'currency': 'USD',
                'base': currency_id,
                'pair': f'{currency_id}-USD'
            }


    db = DatabaseStub()
    coinbase_service = CoinbaseServiceStub()


# Проверяем реальную доступность БД
def check_db_availability():
    """Проверяем реальную доступность БД"""
    try:
        if hasattr(db, 'is_connected'):
            return db.is_connected()
        return DB_AVAILABLE
    except:
        return False


DB_REALLY_AVAILABLE = check_db_availability()

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
    'BTC': {'symbol': 'BTC', 'name': 'Bitcoin', 'emoji': '₿'},
    'ETH': {'symbol': 'ETH', 'name': 'Ethereum', 'emoji': 'Ξ'},
    'BNB': {'symbol': 'BNB', 'name': 'Binance Coin', 'emoji': '🔶'},
    'SOL': {'symbol': 'SOL', 'name': 'Solana', 'emoji': '◎'},
    'XRP': {'symbol': 'XRP', 'name': 'Ripple', 'emoji': '✕'},
    'ADA': {'symbol': 'ADA', 'name': 'Cardano', 'emoji': '₳'},
    'DOGE': {'symbol': 'DOGE', 'name': 'Dogecoin', 'emoji': '🐕'},
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
        'database': 'available' if DB_REALLY_AVAILABLE else 'unavailable',
        'async': True,
        'timestamp': datetime.now().isoformat()
    })


# 🔍 ПОИСК КРИПТОВАЛЮТ - АСИНХРОННЫЙ
@app.route('/api/search', methods=['GET'])
def search_cryptocurrencies():
    query = request.args.get('q', '').strip()

    if not query or len(query) < 1:
        return jsonify({'success': True, 'data': []})

    logger.info(f"🔍 Асинхронный поиск: '{query}'")

    async def perform_search():
        # Сначала ищем в БД (если реально доступна)
        if DB_REALLY_AVAILABLE:
            try:
                db_results = db.search_cryptocurrencies(query)

                if db_results and len(db_results) > 0:
                    results = [
                        {
                            'id': row['coinbase_id'],
                            'symbol': row['symbol'],
                            'name': row['name']
                        }
                        for row in db_results
                    ]
                    logger.info(f"✅ Найдено в БД: {len(results)} результатов")
                    return {'success': True, 'data': results, 'source': 'database'}
            except Exception as e:
                logger.warning(f"⚠️ Ошибка поиска в БД: {e}")

        # Ищем через Coinbase API асинхронно
        try:
            api_results = await coinbase_service.search_currencies(query)

            results = [
                {
                    'id': currency['code'],
                    'symbol': currency['symbol'],
                    'name': currency['name']
                }
                for currency in api_results
            ]

            logger.info(f"✅ Найдено через API: {len(results)} результатов")
            return {'success': True, 'data': results, 'source': 'coinbase'}
        except Exception as e:
            logger.error(f"❌ Ошибка поиска в API: {e}")
            return {'success': True, 'data': [], 'source': 'error'}

    try:
        # Запускаем асинхронную функцию
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(perform_search())
        loop.close()
        return jsonify(result)

    except Exception as e:
        logger.error(f"❌ Ошибка поиска: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# 📊 ВСЕ КРИПТОВАЛЮТЫ
@app.route('/api/cryptos/all', methods=['GET'])
def get_all_cryptocurrencies():
    try:
        if DB_REALLY_AVAILABLE:
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


# 💰 ДАННЫЕ КРИПТОВАЛЮТЫ - АСИНХРОННЫЙ
@app.route('/api/crypto/<crypto_id>', methods=['GET'])
def get_crypto_data(crypto_id):
    logger.info(f"📊 Асинхронный GET /api/crypto/{crypto_id}")

    # Проверка кэша
    cache_key = f"crypto_{crypto_id}"
    if cache_key in cache:
        cached_data, cached_time = cache[cache_key]
        age = time.time() - cached_time
        if age < CACHE_TTL:
            logger.info(f"💾 Кэш ({int(age)}с)")
            return jsonify(cached_data)

    async def fetch_crypto_data():
        # Получаем текущую цену асинхронно
        price_data = await coinbase_service.get_currency_price(crypto_id)

        if not price_data:
            logger.warning(f"⚠️ Не удалось получить данные для {crypto_id}")
            return {'success': False, 'error': f'Не удалось получить данные для {crypto_id}'}

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
        cache[cache_key] = (result, time.time())
        return result

    try:
        # Запускаем асинхронную функцию
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(fetch_crypto_data())
        loop.close()

        if result['success']:
            price = result['data']['current']['price']
            logger.info(f"✅ Успех: {crypto_id} - ${price:,.2f}")
        return jsonify(result)

    except Exception as e:
        logger.error(f"❌ Ошибка получения данных: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# 🔮 ПРОГНОЗ - АСИНХРОННЫЙ
@app.route('/api/predict/<crypto_id>', methods=['POST'])
def predict_price(crypto_id):
    logger.info(f"🔮 Асинхронный прогноз для: {crypto_id}")

    async def make_prediction():
        # Получаем текущую цену для прогноза асинхронно
        price_data = await coinbase_service.get_currency_price(crypto_id)

        if not price_data:
            return {'success': False, 'error': 'Не удалось получить цену'}

        current_price = price_data['price']

        # Простой прогноз
        predictions = simple_prediction(current_price)

        logger.info(f"✅ Прогноз создан для {crypto_id}")

        return {
            'success': True,
            'data': {
                'predictions': predictions,
                'current_price': current_price,
                'predicted_change': 2.5,
                'signal': 'HOLD',
                'signal_text': '🟡 Удержание',
                'days': 7
            }
        }

    try:
        # Запускаем асинхронную функцию
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(make_prediction())
        loop.close()
        return jsonify(result)

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
    print(f"📊 База данных: {'доступна' if DB_REALLY_AVAILABLE else 'недоступна'}")
    print(f"🔍 Поиск: Coinbase API")
    print(f"⚡ Асинхронные запросы: aiohttp")
    print(f"🎯 Все endpoint'ы теперь асинхронные!")
    print(f"{'=' * 60}")
    app.run(host='0.0.0.0', port=port, debug=True)