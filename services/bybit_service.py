import aiohttp
import asyncio
import ssl
import logging
from typing import List, Dict, Optional
import numpy as np

logger = logging.getLogger(__name__)


class BybitService:
    """Асинхронный сервис для работы с Bybit API V5"""

    def __init__(self):
        self.base_url = "https://api.bybit.com"
        self.timeout = aiohttp.ClientTimeout(total=30)

    async def create_session(self):
        """Создание безопасной сессии"""
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
        }

        connector = aiohttp.TCPConnector(
            ssl=ssl_context,
            limit=10,
            force_close=True,
            enable_cleanup_closed=True
        )

        session = aiohttp.ClientSession(
            connector=connector,
            timeout=self.timeout,
            headers=headers,
            trust_env=True
        )

        return session

    async def fetch_url(self, url: str, params: dict = None) -> Optional[dict]:
        """Получить данные с URL"""
        session = await self.create_session()

        try:
            async with session.get(url, params=params, allow_redirects=False) as response:
                if response.status == 200:
                    content_type = response.headers.get('Content-Type', '')

                    if 'application/json' not in content_type:
                        logger.warning(f"Unexpected content type: {content_type}")
                        return None

                    data = await response.json()

                    if data.get('retCode') == 0:
                        return data.get('result')
                    else:
                        logger.warning(f"API error: {data.get('retMsg')}")
                        return None
                else:
                    logger.error(f"HTTP {response.status}")
                    return None

        except asyncio.TimeoutError:
            logger.error("Request timeout")
            return None
        except Exception as e:
            logger.error(f"Error: {e}")
            return None

        finally:
            await session.close()

    async def search_cryptocurrencies(self, query: str) -> List[Dict]:
        """Поиск криптовалют"""
        try:
            url = f"{self.base_url}/v5/market/instruments-info"
            result = await self.fetch_url(url, {"category": "spot"})

            if not result or 'list' not in result:
                logger.warning("Empty search result")
                return []

            query_upper = query.upper()
            filtered = []

            for item in result.get('list', []):
                symbol = item.get('symbol', '')
                base_coin = item.get('baseCoin', '')
                quote_coin = item.get('quoteCoin', '')

                # Только USDT пары
                if quote_coin != 'USDT':
                    continue

                # Проверка совпадения
                if query_upper in symbol or query_upper in base_coin:
                    filtered.append({
                        'symbol': symbol,
                        'name': base_coin,
                        'display_name': base_coin,
                        'emoji': '💰'
                    })

            logger.info(f"Found {len(filtered)} results for '{query}'")
            return filtered[:20]

        except Exception as e:
            logger.error(f"Search error: {e}")
            return []

    async def get_current_price(self, symbol: str) -> Optional[Dict]:
        """Получить текущую цену"""
        try:
            url = f"{self.base_url}/v5/market/tickers"
            result = await self.fetch_url(url, {"category": "spot", "symbol": symbol})

            if not result or 'list' not in result or len(result.get('list', [])) == 0:
                logger.warning(f"No ticker data for {symbol}")
                return None

            ticker = result['list'][0]

            # Получаем необходимые поля с проверками
            try:
                last_price = float(ticker.get('lastPrice', 0))
                prev_price_24h = float(ticker.get('prevPrice24h', last_price))
            except (ValueError, TypeError):
                logger.error(f"Invalid price data for {symbol}")
                return None

            # Рассчитываем изменение
            if prev_price_24h > 0:
                change_24h = ((last_price - prev_price_24h) / prev_price_24h) * 100
            else:
                change_24h = 0

            return {
                'last_price': last_price,
                'change_24h': change_24h,
                'high_24h': float(ticker.get('highPrice24h', last_price)),
                'low_24h': float(ticker.get('lowPrice24h', last_price)),
                'volume_24h': float(ticker.get('volume24h', 0)),
                'turnover_24h': float(ticker.get('turnover24h', 0))
            }

        except Exception as e:
            logger.error(f"Current price error: {e}")
            return None

    async def get_price_history(self, symbol: str, days: int = 90) -> Optional[Dict]:
        """Получить историю цен"""
        try:
            url = f"{self.base_url}/v5/market/kline"
            result = await self.fetch_url(url, {
                "category": "spot",
                "symbol": symbol,
                "interval": "D",
                "limit": min(days, 1000)
            })

            if not result or 'list' not in result:
                logger.warning(f"No history data for {symbol}")
                return None

            klines = result.get('list', [])
            if not klines:
                return None

            # Разворачиваем (API возвращает в обратном порядке)
            klines.reverse()

            # Извлекаем цены и временные метки
            prices = []
            timestamps = []

            for k in klines:
                try:
                    price = float(k[4])  # Close price
                    timestamp = int(k[0])
                    prices.append(price)
                    timestamps.append(timestamp)
                except (ValueError, IndexError, TypeError):
                    logger.warning(f"Invalid kline data: {k}")
                    continue

            if not prices:
                logger.warning(f"No valid prices for {symbol}")
                return None

            logger.info(f"Got {len(prices)} price points for {symbol}")
            return {
                'prices': prices,
                'timestamps': timestamps
            }

        except Exception as e:
            logger.error(f"History error: {e}")
            return None

    async def get_kline_data(self, symbol: str, interval: str = "60", limit: int = 200) -> Optional[List]:
        """Получить свечи"""
        try:
            # Валидация параметров
            valid_intervals = ["1", "5", "15", "30", "60", "120", "240", "360", "720", "D", "W", "M"]
            if interval not in valid_intervals:
                interval = "60"

            limit = min(max(limit, 1), 1000)

            url = f"{self.base_url}/v5/market/kline"
            result = await self.fetch_url(url, {
                "category": "spot",
                "symbol": symbol,
                "interval": interval,
                "limit": limit
            })

            if not result or 'list' not in result:
                logger.warning(f"No kline data for {symbol}")
                return None

            klines = result.get('list', [])
            if not klines:
                return None

            logger.info(f"Got {len(klines)} klines for {symbol}")
            return klines

        except Exception as e:
            logger.error(f"Kline error: {e}")
            return None

    async def calculate_technical_indicators(self, prices: List[float]) -> Dict:
        """Рассчитать технические индикаторы"""
        try:
            if not prices or len(prices) < 2:
                logger.warning("Not enough prices for indicators")
                return self._default_indicators()

            prices_array = np.array(prices, dtype=float)

            # RSI
            rsi = self._calculate_rsi(prices_array)

            # Moving Averages
            ma_7 = float(np.mean(prices_array[-7:])) if len(prices_array) >= 7 else float(prices_array[-1])
            ma_25 = float(np.mean(prices_array[-25:])) if len(prices_array) >= 25 else float(prices_array[-1])
            ma_50 = float(np.mean(prices_array[-50:])) if len(prices_array) >= 50 else float(prices_array[-1])

            # Volatility
            returns = np.diff(prices_array) / prices_array[:-1] * 100
            volatility = float(np.std(returns)) if len(returns) > 0 else 0.0

            # Trend strength
            trend_strength = ((prices_array[-1] - prices_array[0]) / prices_array[0]) * 100 if len(
                prices_array) > 0 else 0.0

            return {
                'rsi': float(rsi),
                'ma_7': float(ma_7),
                'ma_25': float(ma_25),
                'ma_50': float(ma_50),
                'volatility': float(volatility),
                'trend_strength': float(trend_strength)
            }

        except Exception as e:
            logger.error(f"Indicators error: {e}")
            return self._default_indicators()

    def _calculate_rsi(self, prices: np.ndarray, period: int = 14) -> float:
        """Расчет RSI"""
        try:
            if len(prices) < period + 1:
                return 50.0

            deltas = np.diff(prices)
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)

            avg_gain = np.mean(gains[-period:])
            avg_loss = np.mean(losses[-period:])

            if avg_loss == 0:
                return 100.0 if avg_gain > 0 else 50.0

            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

            return float(rsi)

        except Exception as e:
            logger.error(f"RSI calculation error: {e}")
            return 50.0

    def _default_indicators(self) -> Dict:
        """Индикаторы по умолчанию"""
        return {
            'rsi': 50.0,
            'ma_7': 0.0,
            'ma_25': 0.0,
            'ma_50': 0.0,
            'volatility': 0.0,
            'trend_strength': 0.0
        }


# Глобальный экземпляр
bybit_service = BybitService()