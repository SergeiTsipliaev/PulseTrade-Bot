import os

# API settings
COINGECKO_API = 'https://api.coingecko.com/api/v3'
COINCAP_API = 'https://api.coincap.io/v2'

# LSTM settings
SEQUENCE_LENGTH = 60
PREDICTION_DAYS = 7
EPOCHS = 50
BATCH_SIZE = 32

COINCAP_IDS = {
    'bitcoin': 'bitcoin',
    'ethereum': 'ethereum',
    'binancecoin': 'binance-coin',
    'solana': 'solana',
    'ripple': 'xrp'
}

CRYPTOS = {
    'BTC': {'id': 'bitcoin', 'name': 'Bitcoin'},
    'ETH': {'id': 'ethereum', 'name': 'Ethereum'},
    'BNB': {'id': 'binancecoin', 'name': 'Binance Coin'},
    'SOL': {'id': 'solana', 'name': 'Solana'},
    'XRP': {'id': 'ripple', 'name': 'Ripple'},
}

# Bot settings (только для бота, не для API)
BOT_TOKEN = os.getenv('BOT_TOKEN', '')
WEB_APP_URL = os.getenv('WEB_APP_URL', '')