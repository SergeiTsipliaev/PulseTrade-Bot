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
        logger.info("✅ BybitService инициализирован")

    async def create_session(self):
        """ВАЖНО: Создаем НОВУЮ сессию для КАЖДОГО запроса"""
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
            force_close=True,  # ВАЖНО: Закрываем соединения после использования
            enable_cleanup_closed=True
        )

        # trust_env=True позволяет использовать системный VPN
        session = aiohttp.ClientSession(
            connector=connector,
            timeout=self.timeout,
            headers=headers,
            trust_env=True  # ВАЖНО: Используем системные настройки (VPN)
        )

        return session

    async def fetch_url(self, url: str, params: dict = None) -> Optional[dict]:
        """Запрос с НОВОЙ сессией каждый раз"""
        logger.info(f"🌐 Запрос: {url}")
        logger.info(f"📝 Параметры: {params}")

        # Создаем новую сессию для каждого запроса
        session = await self.create_session()

        try:
            for attempt in range(3):
                try:
                    logger.info(f"🔄 Попытка {attempt + 1}/3")

                    async with session.get(url, params=params, allow_redirects=False) as response:
                        logger.info(f"📡 Статус: {response.status}")

                        if response.status in [301, 302, 303, 307, 308]:
                            redirect = response.headers.get('Location', '')
                            logger.error(f"❌ Редирект: {redirect}")

                            if 'prohibited' in redirect.lower():
                                logger.error(f"❌ VPN не работает или отключился!")
                                return None

                            await asyncio.sleep(2)
                            continue

                        if response.status == 200:
                            content_type = response.headers.get('Content-Type', '')

                            if 'application/json' not in content_type:
                                logger.error(f"❌ Не JSON: {content_type}")
                                await asyncio.sleep(2)
                                continue

                            data = await response.json()

                            if data.get('retCode') == 0:
                                logger.info(f"✅ Успех!")
                                return data.get('result')
                            else:
                                logger.error(f"❌ Bybit error: {data.get('retMsg')}")
                                return None
                        else:
                            logger.error(f"❌ HTTP {response.status}")
                            await asyncio.sleep(2)
                            continue

                except aiohttp.ClientError as e:
                    logger.error(f"❌ Ошибка клиента (попытка {attempt + 1}/3): {e}")
                    await asyncio.sleep(2)
                    continue

                except asyncio.TimeoutError:
                    logger.error(f"⏱️ Таймаут (попытка {attempt + 1}/3)")
                    await asyncio.sleep(2)
                    continue

                except Exception as e:
                    logger.error(f"❌ Неожиданная ошибка (попытка {attempt + 1}/3): {e}")
                    await asyncio.sleep(2)
                    continue

            logger.error(f"❌ Все попытки исчерпаны")
            return None

        finally:
            # ВАЖНО: Закрываем сессию после использования
            await session.close()
            logger.info(f"🔒 Сессия закрыта")

    async def search_cryptocurrencies(self, query: str) -> List[Dict]:
        logger.info(f"🔍 Поиск: '{query}'")

        try:
            url = f"{self.base_url}/v5/market/instruments-info"
            result = await self.fetch_url(url, {"category": "spot"})

            if not result or 'list' not in result:
                return []

            query_lower = query.lower().upper()
            filtered = []

            for item in result['list']:
                symbol = item.get('symbol', '')
                base_coin = item.get('baseCoin', '')
                quote_coin = item.get('quoteCoin', '')

                if quote_coin != 'USDT':
                    continue

                if query_lower in symbol or query_lower in base_coin:
                    filtered.append({
                        'symbol': symbol,
                        'name': base_coin,
                        'display_name': base_coin,
                        'emoji': '💰'
                    })

            logger.info(f"✅ Найдено: {len(filtered[:20])}")
            return filtered[:20]

        except Exception as e:
            logger.error(f"❌ Ошибка поиска: {e}")
            return []

    async def get_current_price(self, symbol: str) -> Optional[Dict]:
        logger.info(f"💰 Получение цены: {symbol}")

        try:
            url = f"{self.base_url}/v5/market/tickers"
            result = await self.fetch_url(url, {"category": "spot", "symbol": symbol})

            if result and 'list' in result and len(result['list']) > 0:
                ticker = result['list'][0]
                last_price = float(ticker.get('lastPrice', 0))
                prev_price_24h = float(ticker.get('prevPrice24h', last_price))
                change_24h = ((last_price - prev_price_24h) / prev_price_24h) * 100 if prev_price_24h > 0 else 0

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
        logger.info(f"📊 История: {symbol} за {days} дней")

        try:
            url = f"{self.base_url}/v5/market/kline"
            result = await self.fetch_url(url, {
                "category": "spot",
                "symbol": symbol,
                "interval": "D",
                "limit": min(days, 1000)
            })

            if result and 'list' in result:
                klines = result['list']
                klines.reverse()

                logger.info(f"✅ Получено {len(klines)} свечей")

                return {
                    'prices': [float(k[4]) for k in klines],
                    'timestamps': [int(k[0]) for k in klines]
                }

            return None

        except Exception as e:
            logger.error(f"❌ Ошибка истории: {e}")
            return None

    async def get_kline_data(self, symbol: str, interval: str = "60", limit: int = 200) -> Optional[List]:
        try:
            url = f"{self.base_url}/v5/market/kline"
            result = await self.fetch_url(url, {
                "category": "spot",
                "symbol": symbol,
                "interval": interval,
                "limit": limit
            })
            return result.get('list') if result else None
        except Exception as e:
            logger.error(f"❌ Ошибка получения свечей: {e}")
            return None

    async def calculate_technical_indicators(self, prices: List[float]) -> Dict:
        try:
            prices_array = np.array(prices, dtype=float)
            rsi = self._calculate_rsi(prices_array)
            ma_7 = float(np.mean(prices_array[-7:])) if len(prices_array) >= 7 else prices_array[-1]
            ma_25 = float(np.mean(prices_array[-25:])) if len(prices_array) >= 25 else prices_array[-1]
            ma_50 = float(np.mean(prices_array[-50:])) if len(prices_array) >= 50 else prices_array[-1]
            returns = np.diff(prices_array) / prices_array[:-1] * 100
            volatility = float(np.std(returns))
            trend_strength = ((prices_array[-1] - prices_array[0]) / prices_array[0]) * 100 if len(
                prices_array) > 0 else 0

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
            return {'rsi': 50.0, 'ma_7': 0.0, 'ma_25': 0.0, 'ma_50': 0.0, 'volatility': 0.0, 'trend_strength': 0.0}

    def _calculate_rsi(self, prices: np.ndarray, period: int = 14) -> float:
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


bybit_service = BybitService()
logger.info("🚀 bybit_service создан")