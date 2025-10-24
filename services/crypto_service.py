import sys
import os
import aiohttp
import numpy as np
from datetime import datetime, timedelta
from config import COINGECKO_API


class CryptoService:
    """Сервис для работы с криптовалютными данными"""

    @staticmethod
    async def get_current_price(crypto_id: str):
        """Получить текущую цену и данные"""
        url = f"{COINGECKO_API}/coins/{crypto_id}"
        params = {
            'localization': 'false',
            'tickers': 'false',
            'community_data': 'false',
            'developer_data': 'false'
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        'price': data['market_data']['current_price']['usd'],
                        'change_24h': data['market_data']['price_change_percentage_24h'],
                        'change_7d': data['market_data']['price_change_percentage_7d'],
                        'change_30d': data['market_data']['price_change_percentage_30d'],
                        'high_24h': data['market_data']['high_24h']['usd'],
                        'low_24h': data['market_data']['low_24h']['usd'],
                        'market_cap': data['market_data']['market_cap']['usd'],
                        'volume_24h': data['market_data']['total_volume']['usd'],
                        'circulating_supply': data['market_data']['circulating_supply'],
                        'ath': data['market_data']['ath']['usd'],
                        'atl': data['market_data']['atl']['usd']
                    }
                return None

    @staticmethod
    async def get_price_history(crypto_id: str, days: int = 90):
        """Получить историю цен"""
        url = f"{COINGECKO_API}/coins/{crypto_id}/market_chart"
        params = {
            'vs_currency': 'usd',
            'days': days,
            'interval': 'daily' if days > 1 else 'hourly'
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    prices = [price[1] for price in data['prices']]
                    timestamps = [price[0] for price in data['prices']]

                    return {
                        'prices': prices,
                        'timestamps': timestamps,
                        'volumes': [vol[1] for vol in data['total_volumes']]
                    }
                return None

    @staticmethod
    def calculate_technical_indicators(prices):
        """Расчет технических индикаторов"""
        prices_array = np.array(prices)

        # RSI (Relative Strength Index)
        deltas = np.diff(prices_array)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.mean(gains[-14:]) if len(gains) >= 14 else 0
        avg_loss = np.mean(losses[-14:]) if len(losses) >= 14 else 0

        rs = avg_gain / avg_loss if avg_loss != 0 else 0
        rsi = 100 - (100 / (1 + rs))

        # Moving Averages
        ma_7 = np.mean(prices_array[-7:]) if len(prices_array) >= 7 else prices_array[-1]
        ma_25 = np.mean(prices_array[-25:]) if len(prices_array) >= 25 else prices_array[-1]
        ma_50 = np.mean(prices_array[-50:]) if len(prices_array) >= 50 else prices_array[-1]

        # Volatility
        returns = np.diff(prices_array) / prices_array[:-1]
        volatility = np.std(returns) * 100

        # Trend
        if len(prices_array) >= 2:
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
