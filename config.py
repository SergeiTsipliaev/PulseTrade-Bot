import os
from dotenv import load_dotenv

load_dotenv()

# ======================== BYBIT API ========================
BYBIT_API_BASE = 'https://api.bybit.com'
BYBIT_PUBLIC_ENDPOINT = '/v5/market'

# ======================== DATABASE ========================
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = int(os.getenv('DB_PORT', '5432'))
DB_NAME = os.getenv('DB_NAME', 'cryptobot')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'postgres')

# Database URL
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# ======================== TELEGRAM BOT ========================
BOT_TOKEN = os.getenv('BOT_TOKEN', '')
WEB_APP_URL = os.getenv('WEB_APP_URL', 'http://localhost:5000')

# ======================== FLASK ========================
FLASK_ENV = os.getenv('FLASK_ENV', 'development')
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
DEBUG = FLASK_ENV == 'development'

# ======================== LSTM SETTINGS ========================
SEQUENCE_LENGTH = 60
PREDICTION_DAYS = 7
EPOCHS = 50
BATCH_SIZE = 32

# ======================== CACHE SETTINGS ========================
CACHE_TTL = 300  # 5 minutes
PRICE_HISTORY_DAYS = 90

# ======================== POPULAR CRYPTOS (BYBIT SYMBOLS) ========================
POPULAR_CRYPTOS = [
    {'symbol': 'BTCUSDT', 'name': 'Bitcoin', 'display_name': 'BTC', 'emoji': '₿'},
    {'symbol': 'ETHUSDT', 'name': 'Ethereum', 'display_name': 'ETH', 'emoji': 'Ξ'},
    {'symbol': 'BNBUSDT', 'name': 'Binance Coin', 'display_name': 'BNB', 'emoji': '🔶'},
    {'symbol': 'SOLUSDT', 'name': 'Solana', 'display_name': 'SOL', 'emoji': '◎'},
    {'symbol': 'XRPUSDT', 'name': 'Ripple', 'display_name': 'XRP', 'emoji': '✕'},
    {'symbol': 'ADAUSDT', 'name': 'Cardano', 'display_name': 'ADA', 'emoji': '₳'},
]

# ======================== API LIMITS ========================
API_REQUEST_TIMEOUT = 15
MAX_SEARCH_RESULTS = 20

# ======================== LOGGING ========================
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = 'logs/app.log'

os.makedirs('logs', exist_ok=True)