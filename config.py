import os
from dotenv import load_dotenv

load_dotenv()


class BybitConfig:
    API_KEY = os.getenv('BYBIT_API_KEY')
    API_SECRET = os.getenv('BYBIT_API_SECRET')
    BASE_URL = os.getenv('BYBIT_BASE_URL', 'https://api.bybit.com')
    WS_URL = os.getenv('BYBIT_WS_URL', 'wss://stream.bybit.com/v5/public/spot')
    WS_PRIVATE_URL = os.getenv('BYBIT_WS_PRIVATE_URL', 'wss://stream.bybit.com/v5/private')

    TESTNET = os.getenv('BYBIT_TESTNET', 'true').lower() == 'true'

    if TESTNET:
        BASE_URL = 'https://api-testnet.bybit.com'
        WS_URL = 'wss://stream-testnet.bybit.com/v5/public/spot'
        WS_PRIVATE_URL = 'wss://stream-testnet.bybit.com/v5/private'


class TelegramConfig:
    BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')


class TradingConfig:
    DEFAULT_SYMBOL = os.getenv('DEFAULT_SYMBOL', 'BTCUSDT')
    LEVERAGE = int(os.getenv('LEVERAGE', '10'))
    RISK_PERCENT = float(os.getenv('RISK_PERCENT', '1.0'))
    UPDATE_INTERVAL = int(os.getenv('UPDATE_INTERVAL', '1'))


class ModelConfig:
    SEQUENCE_LENGTH = int(os.getenv('SEQUENCE_LENGTH', '60'))
    TRAINING_EPOCHS = int(os.getenv('TRAINING_EPOCHS', '50'))
    PREDICTION_DAYS = int(os.getenv('PREDICTION_DAYS', '7'))