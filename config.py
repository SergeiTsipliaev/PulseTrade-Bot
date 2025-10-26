import os

# Coinbase API (10,000 requests/hour - бесплатно!)
COINBASE_API = 'https://api.coinbase.com/v2'

# Mapping crypto IDs
COINBASE_SYMBOLS = {
    'bitcoin': 'BTC',
    'ethereum': 'ETH',
    'binancecoin': 'BNB',
    'solana': 'SOL',
    'ripple': 'XRP'
}

# LSTM settings
SEQUENCE_LENGTH = 60
PREDICTION_DAYS = 7
EPOCHS = 50
BATCH_SIZE = 32

CRYPTOS = {
    'bitcoin': {'id': 'bitcoin', 'symbol': 'BTC', 'name': 'Bitcoin'},
    'ethereum': {'id': 'ethereum', 'symbol': 'ETH', 'name': 'Ethereum'},
    'binancecoin': {'id': 'binancecoin', 'symbol': 'BNB', 'name': 'BNB'},
    'solana': {'id': 'solana', 'symbol': 'SOL', 'name': 'Solana'},
    'ripple': {'id': 'ripple', 'symbol': 'XRP', 'name': 'XRP'},
}

# Bot settings
BOT_TOKEN = os.getenv('BOT_TOKEN', '')
WEB_APP_URL = os.getenv('WEB_APP_URL', '')