import aiohttp
import asyncio
import ssl
import certifi
from models.database import db


class CoinbaseService:
    def __init__(self):
        self.base_url = "https://api.coinbase.com/v2"

    def create_ssl_context(self):
        """Создание SSL контекста"""
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        return ssl_context

    async def search_currencies(self, query):
        """Поиск криптовалют через Coinbase API"""
        ssl_context = self.create_ssl_context()
        connector = aiohttp.TCPConnector(ssl=ssl_context)

        async with aiohttp.ClientSession(connector=connector) as session:
            try:
                # Получаем список всех валют
                url = f"{self.base_url}/currencies/crypto"
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        currencies = data.get('data', [])

                        # Фильтруем по запросу
                        filtered = [
                            currency for currency in currencies
                            if query.lower() in currency['name'].lower() or
                               query.lower() in currency['symbol'].lower()
                        ]

                        # Сохраняем в БД
                        for currency in filtered[:20]:  # Ограничиваем количество
                            db.add_cryptocurrency(
                                currency['code'],
                                currency['symbol'],
                                currency['name']
                            )

                        return filtered[:10]  # Возвращаем топ-10 результатов

            except Exception as e:
                print(f"❌ Ошибка поиска в Coinbase: {e}")
                return []

    async def get_currency_price(self, currency_id):
        """Получение цены криптовалюты"""
        ssl_context = self.create_ssl_context()
        connector = aiohttp.TCPConnector(ssl=ssl_context)

        async with aiohttp.ClientSession(connector=connector) as session:
            try:
                # Пробуем разные пары
                pairs = [f"{currency_id}-USD", f"{currency_id}-USDT", f"{currency_id}-EUR"]

                for pair in pairs:
                    url = f"{self.base_url}/prices/{pair}/spot"
                    async with session.get(url, timeout=5) as response:
                        if response.status == 200:
                            data = await response.json()
                            return {
                                'price': float(data['data']['amount']),
                                'currency': data['data']['currency'],
                                'base': data['data']['base']
                            }

                return None

            except Exception as e:
                print(f"❌ Ошибка получения цены {currency_id}: {e}")
                return None


# Глобальный экземпляр сервиса
coinbase_service = CoinbaseService()