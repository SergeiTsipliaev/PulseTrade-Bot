import aiohttp
import asyncio
import ssl
import certifi
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class BybitService:
    """Сервис для работы с Bybit API V5"""

    def __init__(self):
        self.base_url = "https://api.bybit.com"
        self.timeout = aiohttp.ClientTimeout(total=15)
        self._session = None

    def create_ssl_context(self):
        """Создание SSL контекста"""
        try:
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            return ssl_context
        except Exception as e:
            logger.warning(f"⚠️ SSL контекст: {e}")
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            return ssl_context

    async def get_session(self):
        """Получение или создание сессии"""
        if self._session is None or self._session.closed:
            ssl_context = self.create_ssl_context()
            connector = aiohttp.TCPConnector(ssl=ssl_context, limit=10)
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=self.timeout
            )
        return self._session

    async def close_session(self):
        """Закрытие сессии"""
        if self._session and not self._session.closed:
            await self._session.close()

    async def fetch_url(self, url: str, params: dict = None) -> Optional[dict]:
        """Асинхронный запрос"""
        session = await self.get_session()
        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('retCode') == 0:
                        return data.get('result')
                    else:
                        logger.warning(f"❌ Bybit error: {data.get('retMsg')}")
                        return None
                else:
                    logger.warning(f"❌ HTTP {response.status} для {url}")
                    return None
        except asyncio.TimeoutError:
            logger.warning(f"⏱️ Таймаут для {url}")
            return None
        except Exception as e:
            logger.error(f"❌ Ошибка запроса {url}: {e}")
            return None

    async def get_tickers(self, category: str = "spot") -> List[Dict]:
        """Получение списка всех тикеров"""
        url = f"{self.base_url}/v5/market/tickers"
        params = {"category": category}

        result = await self.fetch_url(url, params)
        if result and 'list' in result:
            return result['list']
        return []

    async def search_currencies(self, query: str) -> List[Dict]:
        """Поиск криптовалют"""
        logger.info(f"🔍 Поиск: {query}")

        # Получаем все тикеры
        tickers = await self.get_tickers()

        if not tickers:
            return []

        # Фильтруем по запросу
        query_lower = query.lower()
        filtered = []

        for ticker in tickers:
            symbol = ticker.get('symbol', '')

            # Извлекаем базовую валюту (например, BTC из BTCUSDT)
            base_currency = symbol.replace('USDT', '').replace('USDC', '').replace('USD', '')

            if (query_lower in base_currency.lower() or
                    query_lower in symbol.lower()):
                filtered.append({
                    'code': base_currency,
                    'symbol': base_currency,
                    'name': base_currency,
                    'pair': symbol
                })

        # Убираем дубликаты
        seen = set()
        unique = []
        for item in filtered:
            if item['code'] not in seen:
                seen.add(item['code'])
                unique.append(item)

        logger.info(f"✅ Найдено: {len(unique)} криптовалют")
        return unique[:20]

    async def get_currency_price(self, currency_id: str) -> Optional[Dict]:
        """Получение текущей цены"""
        logger.info(f"💰 Получение цены: {currency_id}")

        # Формируем возможные пары
        pairs = [
            f"{currency_id.upper()}USDT",
            f"{currency_id.upper()}USD",
            f"{currency_id.upper()}USDC"
        ]

        for pair in pairs:
            url = f"{self.base_url}/v5/market/tickers"
            params = {
                "category": "spot",
                "symbol": pair
            }

            result = await self.fetch_url(url, params)

            if result and 'list' in result and len(result['list']) > 0:
                ticker = result['list'][0]

                last_price = float(ticker.get('lastPrice', 0))
                prev_price_24h = float(ticker.get('prevPrice24h', last_price))

                # Расчет изменения за 24ч
                if prev_price_24h > 0:
                    change_24h = ((last_price - prev_price_24h) / prev_price_24h) * 100
                else:
                    change_24h = 0

                return {
                    'price': last_price,
                    'currency': 'USD',
                    'base': currency_id.upper(),
                    'pair': pair,
                    'change_24h': change_24h,
                    'volume_24h': float(ticker.get('volume24h', 0)),
                    'high_24h': float(ticker.get('highPrice24h', 0)),
                    'low_24h': float(ticker.get('lowPrice24h', 0))
                }

        logger.warning(f"⚠️ Цена не найдена для {currency_id}")
        return None

    async def get_kline_history(self, currency_id: str, interval: str = "D", limit: int = 90) -> Optional[Dict]:
        """Получение исторических данных (свечей)"""
        logger.info(f"📊 Получение истории: {currency_id}")

        # Формируем пары
        pairs = [
            f"{currency_id.upper()}USDT",
            f"{currency_id.upper()}USD",
            f"{currency_id.upper()}USDC"
        ]

        for pair in pairs:
            url = f"{self.base_url}/v5/market/kline"

            # Рассчитываем временные метки
            end_time = int(datetime.now().timestamp() * 1000)

            params = {
                "category": "spot",
                "symbol": pair,
                "interval": interval,  # D = daily
                "limit": limit,
                "end": end_time
            }

            result = await self.fetch_url(url, params)

            if result and 'list' in result and len(result['list']) > 0:
                klines = result['list']

                # Bybit возвращает данные в обратном порядке (от новых к старым)
                klines.reverse()

                prices = []
                timestamps = []
                volumes = []

                for kline in klines:
                    # Формат: [startTime, openPrice, highPrice, lowPrice, closePrice, volume, turnover]
                    timestamp = int(kline[0])
                    close_price = float(kline[4])
                    volume = float(kline[5])

                    timestamps.append(timestamp)
                    prices.append(close_price)
                    volumes.append(volume)

                logger.info(f"✅ Получено {len(prices)} свечей для {pair}")

                return {
                    'prices': prices,
                    'timestamps': timestamps,
                    'volumes': volumes,
                    'pair': pair
                }

        logger.warning(f"⚠️ История не найдена для {currency_id}")
        return None

    async def get_all_spot_symbols(self) -> List[Dict]:
        """Получение всех спотовых символов для БД"""
        logger.info("📋 Получение всех спотовых символов...")

        url = f"{self.base_url}/v5/market/instruments-info"
        params = {"category": "spot"}

        result = await self.fetch_url(url, params)

        if result and 'list' in result:
            symbols = []
            for item in result['list']:
                symbol = item.get('symbol', '')
                base_coin = item.get('baseCoin', '')

                if base_coin and 'USDT' in symbol:
                    symbols.append({
                        'coinbase_id': base_coin,
                        'symbol': base_coin,
                        'name': base_coin,
                        'pair': symbol
                    })

            logger.info(f"✅ Получено {len(symbols)} символов")
            return symbols

        return []


# Глобальный экземпляр
BybitServise = BybitService()