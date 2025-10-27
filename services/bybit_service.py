import aiohttp
import asyncio
import ssl
import certifi
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import numpy as np

logger = logging.getLogger(__name__)


class BybitService:
    """Асинхронный сервис для работы с Bybit API V5"""

    def __init__(self):
        self.base_url = "https://api.bybit.com"
        self.timeout = aiohttp.ClientTimeout(total=15)
        self._session = None

    def create_ssl_context(self):
        """Создание SSL контекста"""
        try:
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            return ssl_context
        except:
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
        """Асинхронный запрос к API"""
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
                    logger.warning(f"❌ HTTP {response.status}")
                    return None
        except asyncio.TimeoutError:
            logger.warning(f"⏱️ Таймаут запроса")
            return None
        except Exception as e:
            logger.error(f"❌ Ошибка запроса: {e}")
            return None

    async def search_cryptocurrencies(self, query: str) -> List[Dict]:
        """Поиск криптовалют по запросу"""
        logger.info(f"🔍 Поиск: '{query}'")

        try:
            url = f"{self.base_url}/v5/market/instruments-info"
            params = {"category": "spot"}

            result = await self.fetch_url(url, params)

            if not result or 'list' not in result:
                return []

            query_lower = query.lower().upper()
            filtered = []

            for item in result['list']:
                symbol = item.get('symbol', '')
                base_coin = item.get('baseCoin', '')
                quote_coin = item.get('quoteCoin', '')

                # Ищем USDT пары
                if quote_coin != 'USDT':
                    continue

                if query_lower in symbol or query_lower in base_coin:
                    filtered.append({
                        'symbol': symbol,
                        'name': base_coin,
                        'display_name': base_coin,
                        'emoji': '💰'
                    })

            logger.info(f"✅ Найдено: {len(filtered[:20])} криптовалют")
            return filtered[:20]

        except Exception as e:
            logger.error(f"❌ Ошибка поиска: {e}")
            return []

    async def get_current_price(self, symbol: str) -> Optional[Dict]:
        """Получение текущей цены"""
        logger.info(f"💰 Получение цены: {symbol}")

        try:
            url = f"{self.base_url}/v5/market/tickers"
            params = {
                "category": "spot",
                "symbol": symbol
            }

            result = await self.fetch_url(url, params)

            if result and 'list' in result and len(result['list']) > 0:
                ticker = result['list'][0]

                last_price = float(ticker.get('lastPrice', 0))
                prev_price_24h = float(ticker.get('prevPrice24h', last_price))

                change_24h = 0
                if prev_price_24h > 0:
                    change_24h = ((last_price - prev_price_24h) / prev_price_24h) * 100

                logger.info(f"✅ Цена {symbol}: ${last_price}")

                return {
                    'last_price': last_price,
                    'change_24h': change_24h,
                    'high_24h': float(ticker.get('highPrice24h', last_price)),
                    'low_24h': float(ticker.get('lowPrice24h', last_price)),
                    'volume_24h': float(ticker.get('volume24h', 0)),
                    'turnover_24h': float(ticker.get('turnover24h', 0))
                }

            return None

        except Exception as e:
            logger.error(f"❌ Ошибка получения цены: {e}")
            return None

    async def get_price_history(self, symbol: str, days: int = 90) -> Optional[Dict]:
        """Получение исторических данных (свечи за дни)"""
        logger.info(f"📊 Получение истории: {symbol} за {days} дней")

        try:
            # Получаем дневные свечи
            url = f"{self.base_url}/v5/market/kline"
            params = {
                "category": "spot",
                "symbol": symbol,
                "interval": "D",
                "limit": min(days, 1000)
            }

            result = await self.fetch_url(url, params)

            if result and 'list' in result and len(result['list']) > 0:
                klines = result['list']
                klines.reverse()  # От старых к новым

                prices = []
                timestamps = []

                for kline in klines:
                    timestamp = int(kline[0])
                    close_price = float(kline[4])

                    timestamps.append(timestamp)
                    prices.append(close_price)

                logger.info(f"✅ Получено {len(prices)} свечей")

                return {
                    'prices': prices,
                    'timestamps': timestamps
                }

            return None

        except Exception as e:
            logger.error(f"❌ Ошибка получения истории: {e}")
            return None

    async def get_kline_data(self, symbol: str, interval: str = "60", limit: int = 200) -> Optional[List]:
        """Получение свечей"""
        logger.info(f"📊 Свечи: {symbol}")

        try:
            url = f"{self.base_url}/v5/market/kline"
            params = {
                "category": "spot",
                "symbol": symbol,
                "interval": interval,
                "limit": limit
            }

            result = await self.fetch_url(url, params)

            if result and 'list' in result:
                return result['list']

            return None

        except Exception as e:
            logger.error(f"❌ Ошибка: {e}")
            return None

    async def calculate_technical_indicators(self, prices: List[float]) -> Dict:
        """Расчет технических индикаторов"""
        try:
            prices_array = np.array(prices, dtype=float)

            # RSI
            rsi = self._calculate_rsi(prices_array)

            # Moving Averages
            ma_7 = float(np.mean(prices_array[-7:])) if len(prices_array) >= 7 else prices_array[-1]
            ma_25 = float(np.mean(prices_array[-25:])) if len(prices_array) >= 25 else prices_array[-1]
            ma_50 = float(np.mean(prices_array[-50:])) if len(prices_array) >= 50 else prices_array[-1]

            # Volatility
            returns = np.diff(prices_array) / prices_array[:-1] * 100
            volatility = float(np.std(returns))

            # Trend
            if len(prices_array) > 0:
                trend_strength = ((prices_array[-1] - prices_array[0]) / prices_array[0]) * 100
            else:
                trend_strength = 0

            return {
                'rsi': float(rsi),
                'ma_7': float(ma_7),
                'ma_25': float(ma_25),
                'ma_50': float(ma_50),
                'volatility': float(volatility),
                'trend_strength': float(trend_strength)
            }

        except Exception as e:
            logger.error(f"❌ Ошибка расчета индикаторов: {e}")
            return {
                'rsi': 50.0,
                'ma_7': 0.0,
                'ma_25': 0.0,
                'ma_50': 0.0,
                'volatility': 0.0,
                'trend_strength': 0.0
            }

    def _calculate_rsi(self, prices: np.ndarray, period: int = 14) -> float:
        """Расчет RSI"""
        try:
            if len(prices) < period:
                return 50.0

            deltas = np.diff(prices)
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)

            avg_gain = np.mean(gains[-period:])
            avg_loss = np.mean(losses[-period:])

            rs = avg_gain / avg_loss if avg_loss > 0 else 0
            rsi = 100 - (100 / (1 + rs)) if rs >= 0 else 50

            return float(rsi)
        except:
            return 50.0


# Глобальный экземпляр
bybit_service = BybitService()