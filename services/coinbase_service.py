import aiohttp
import asyncio
import ssl
import certifi
import logging
import sys
import os

# Добавляем корневую директорию в путь
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
sys.path.insert(0, project_root)

from models.database import db

logger = logging.getLogger(__name__)


class CoinbaseService:
    def __init__(self):
        self.base_url = "https://api.coinbase.com/v2"
        self.timeout = aiohttp.ClientTimeout(total=10)

    def create_ssl_context(self):
        """Создание SSL контекста"""
        try:
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            return ssl_context
        except Exception as e:
            logger.warning(f"⚠️ Ошибка создания SSL контекста: {e}")
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            return ssl_context

    async def fetch_url(self, session, url, params=None):
        """Асинхронный запрос с обработкой ошибок"""
        try:
            async with session.get(url, params=params, timeout=self.timeout) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.warning(f"❌ HTTP {response.status} для {url}")
                    return None
        except asyncio.TimeoutError:
            logger.warning(f"⏱️ Таймаут для {url}")
            return None
        except Exception as e:
            logger.error(f"❌ Ошибка запроса {url}: {e}")
            return None

    async def search_currencies(self, query):
        """Асинхронный поиск криптовалют через Coinbase API"""
        ssl_context = self.create_ssl_context()
        connector = aiohttp.TCPConnector(ssl=ssl_context)

        async with aiohttp.ClientSession(connector=connector) as session:
            try:
                # Получаем список всех криптовалют
                url = f"{self.base_url}/currencies/crypto"
                data = await self.fetch_url(session, url)

                if not data:
                    return []

                currencies = data.get('data', [])

                # Фильтруем по запросу
                filtered = [
                    currency for currency in currencies
                    if query.lower() in currency.get('name', '').lower() or
                       query.lower() in currency.get('symbol', '').lower()
                ]

                # Сохраняем в БД
                for currency in filtered[:20]:
                    db.add_cryptocurrency(
                        currency.get('code', ''),
                        currency.get('symbol', ''),
                        currency.get('name', '')
                    )

                logger.info(f"🔍 Найдено {len(filtered)} криптовалют для запроса '{query}'")
                return filtered[:10]

            except Exception as e:
                logger.error(f"❌ Ошибка поиска в Coinbase: {e}")
                return []

    async def get_currency_price(self, currency_id):
        """Асинхронное получение цены криптовалюты"""
        ssl_context = self.create_ssl_context()
        connector = aiohttp.TCPConnector(ssl=ssl_context)

        async with aiohttp.ClientSession(connector=connector) as session:
            try:
                # Пробуем разные торговые пары
                pairs = [f"{currency_id}-USD", f"{currency_id}-USDT", f"{currency_id}-EUR"]

                for pair in pairs:
                    url = f"{self.base_url}/prices/{pair}/spot"
                    data = await self.fetch_url(session, url)

                    if data and 'data' in data:
                        price_data = data['data']
                        return {
                            'price': float(price_data['amount']),
                            'currency': price_data['currency'],
                            'base': price_data['base'],
                            'pair': pair
                        }

                logger.warning(f"⚠️ Не удалось получить цену для {currency_id}")
                return None

            except Exception as e:
                logger.error(f"❌ Ошибка получения цены {currency_id}: {e}")
                return None


# Глобальный экземпляр сервиса
coinbase_service = CoinbaseService()