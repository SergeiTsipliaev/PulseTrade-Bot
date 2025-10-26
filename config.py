import os

# Database settings
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_NAME = os.getenv('DB_NAME', 'cryptobot')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'password')
DB_PORT = os.getenv('DB_PORT', '5432')

# Database URL for SQLAlchemy
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Coinbase API
COINBASE_API = 'https://api.coinbase.com/v2'

# LSTM settings (если будете использовать)
SEQUENCE_LENGTH = 60
PREDICTION_DAYS = 7
EPOCHS = 50
BATCH_SIZE = 32

# Bot settings
BOT_TOKEN = os.getenv('BOT_TOKEN', '')
WEB_APP_URL = os.getenv('WEB_APP_URL', '')

# Cache settings
CACHE_TTL = 60  # seconds

# Popular cryptocurrencies for default display
POPULAR_CRYPTOS = {
    'BTC': {'symbol': 'BTC', 'name': 'Bitcoin'},
    'ETH': {'symbol': 'ETH', 'name': 'Ethereum'},
    'BNB': {'symbol': 'BNB', 'name': 'Binance Coin'},
    'SOL': {'symbol': 'SOL', 'name': 'Solana'},
    'XRP': {'symbol': 'XRP', 'name': 'Ripple'},
    'ADA': {'symbol': 'ADA', 'name': 'Cardano'},
    'DOGE': {'symbol': 'DOGE', 'name': 'Dogecoin'},
    'DOT': {'symbol': 'DOT', 'name': 'Polkadot'},
    'LTC': {'symbol': 'LTC', 'name': 'Litecoin'},
    'MATIC': {'symbol': 'MATIC', 'name': 'Polygon'}
}