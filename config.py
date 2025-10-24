import os

# API settings
COINGECKO_API = 'https://api.coingecko.com/api/v3'

# LSTM settings
SEQUENCE_LENGTH = 60
PREDICTION_DAYS = 7
EPOCHS = 50
BATCH_SIZE = 32

CRYPTOS = {
    'BTC': {'id': 'bitcoin', 'name': 'Bitcoin'},
    'ETH': {'id': 'ethereum', 'name': 'Ethereum'},
    'BNB': {'id': 'binancecoin', 'name': 'Binance Coin'},
    'SOL': {'id': 'solana', 'name': 'Solana'},
    'XRP': {'id': 'ripple', 'name': 'Ripple'},
}

# Bot settings (только для бота, не для API)
BOT_TOKEN = os.getenv('BOT_TOKEN', '7573870990:AAF8ebxWevgeIZAjjjJOlHaWMcOX5dUzbTU')
WEB_APP_URL = os.getenv('WEB_APP_URL', '')