import requests
import numpy as np
from datetime import datetime, timedelta
import certifi


class CryptoService:
    """Сервис для работы с Coinbase и CryptoCompare API"""

    COINBASE_API = 'https://api.coinbase.com/v2'
    CRYPTOCOMPARE_API = 'https://min-api.cryptocompare.com/data/v2'

    SYMBOLS = {
        'bitcoin': 'BTC-USD',
        'ethereum': 'ETH-USD',
        'binancecoin': 'BNB-USD',
        'solana': 'SOL-USD',
        'ripple': 'XRP-USD'
    }

    @staticmethod
    def make_request(url, params=None):
        """Безопасный HTTP запрос"""
        try:
            response = requests.get(url, params=params, timeout=10, verify=certifi.where())
            return response
        except requests.exceptions.SSLError:
            response = requests.get(url, params=params, timeout=10, verify=False)
            return response
        except Exception as e:
            print(f"Request error: {e}")
            return None

    @staticmethod
    def get_current_price(crypto_id: str):
        """Получить текущую цену из Coinbase"""
        pair = CryptoService.SYMBOLS.get(crypto_id, 'BTC-USD')
        url = f"{CryptoService.COINBASE_API}/prices/{pair}/spot"

        response = CryptoService.make_request(url)
        if response and response.status_code == 200:
            data = response.json()
            return {
                'price': float(data['data']['amount']),
                'currency': data['data']['currency']
            }
        return None

    @staticmethod
    def get_price_history(crypto_id: str, days: int = 90):
        """Получить историю цен из CryptoCompare"""
        symbol = CryptoService.SYMBOLS.get(crypto_id, 'BTC-USD').split('-')[0]
        url = f"{CryptoService.CRYPTOCOMPARE_API}/histoday"
        params = {
            'fsym': symbol,
            'tsym': 'USD',
            'limit': days
        }

        response = CryptoService.make_request(url, params)
        if response and response.status_code == 200:
            data = response.json()
            if data.get('Response') == 'Success':
                history_data = data['Data']['Data']
                prices = [float(d['close']) for d in history_data]
                timestamps = [d['time'] * 1000 for d in history_data]
                volumes = [float(d['volumeto']) for d in history_data]

                return {
                    'prices': prices,
                    'timestamps': timestamps,
                    'volumes': volumes
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