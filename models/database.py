import psycopg2
from psycopg2.extras import RealDictCursor
import os
import logging
import sys

# Добавляем корневую директорию в путь
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
sys.path.insert(0, project_root)

logger = logging.getLogger(__name__)


class Database:
    def __init__(self):
        self.conn = None
        self.connect()

    def connect(self):
        """Подключение к PostgreSQL с обработкой ошибок"""
        try:
            self.conn = psycopg2.connect(
                host=os.getenv('DB_HOST', 'localhost'),
                database=os.getenv('DB_NAME', 'cryptobot'),
                user=os.getenv('DB_USER', 'postgres'),
                password=os.getenv('DB_PASSWORD', 'password'),
                port=os.getenv('DB_PORT', '5432'),
                connect_timeout=5
            )
            self.create_tables()
            logger.info("✅ Подключение к PostgreSQL установлено")
            return True
        except Exception as e:
            logger.warning(f"⚠️ PostgreSQL недоступна: {e}")
            logger.info("🔄 Работаем в режиме без базы данных")
            self.conn = None
            return False

    def is_connected(self):
        """Проверка подключения к БД"""
        return self.conn is not None

    def create_tables(self):
        """Создание таблиц (только если БД доступна)"""
        if not self.conn:
            return

        try:
            with self.conn.cursor() as cur:
                # Таблица криптовалют
                cur.execute("""
                            CREATE TABLE IF NOT EXISTS cryptocurrencies
                            (
                                id
                                SERIAL
                                PRIMARY
                                KEY,
                                coinbase_id
                                VARCHAR
                            (
                                50
                            ) UNIQUE NOT NULL,
                                symbol VARCHAR
                            (
                                20
                            ) NOT NULL,
                                name VARCHAR
                            (
                                100
                            ) NOT NULL,
                                is_active BOOLEAN DEFAULT TRUE,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                                )
                            """)

                # Индексы для быстрого поиска
                cur.execute("""
                            CREATE INDEX IF NOT EXISTS idx_crypto_symbol
                                ON cryptocurrencies(symbol)
                            """)
                cur.execute("""
                            CREATE INDEX IF NOT EXISTS idx_crypto_name
                                ON cryptocurrencies(name)
                            """)

                self.conn.commit()
                logger.info("✅ Таблицы созданы/проверены")
        except Exception as e:
            logger.error(f"❌ Ошибка создания таблиц: {e}")
            if self.conn:
                self.conn.rollback()

    def search_cryptocurrencies(self, query):
        """Поиск криптовалют в БД"""
        if not self.is_connected():
            logger.debug("🔍 Поиск: БД недоступна, возвращаем пустой список")
            return []

        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                            SELECT coinbase_id, symbol, name
                            FROM cryptocurrencies
                            WHERE (LOWER(symbol) LIKE LOWER(%s) OR LOWER(name) LIKE LOWER(%s))
                              AND is_active = TRUE
                            ORDER BY CASE
                                         WHEN LOWER(symbol) = LOWER(%s) THEN 1
                                         WHEN LOWER(name) = LOWER(%s) THEN 2
                                         ELSE 3
                                         END,
                                     symbol LIMIT 20
                            """, (f'{query}%', f'%{query}%', query, query))

                results = cur.fetchall()
                logger.debug(f"🔍 Найдено в БД: {len(results)} результатов для '{query}'")
                return results
        except Exception as e:
            logger.error(f"❌ Ошибка поиска в БД: {e}")
            return []

    def add_cryptocurrency(self, coinbase_id, symbol, name):
        """Добавление криптовалюты в БД"""
        if not self.is_connected():
            logger.debug(f"💾 Пропускаем сохранение {symbol} - БД недоступна")
            return False

        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                            INSERT INTO cryptocurrencies (coinbase_id, symbol, name)
                            VALUES (%s, %s, %s) ON CONFLICT (coinbase_id) 
                    DO
                            UPDATE SET
                                symbol = EXCLUDED.symbol,
                                name = EXCLUDED.name,
                                updated_at = CURRENT_TIMESTAMP
                            """, (coinbase_id, symbol, name))
                self.conn.commit()
                logger.debug(f"💾 Сохранена криптовалюта: {symbol} - {name}")
                return True
        except Exception as e:
            logger.error(f"❌ Ошибка добавления криптовалюты: {e}")
            if self.conn:
                self.conn.rollback()
            return False

    def get_all_cryptocurrencies(self):
        """Получение всех криптовалют"""
        if not self.is_connected():
            logger.debug("📋 Получение списка: БД недоступна")
            return []

        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                            SELECT coinbase_id, symbol, name
                            FROM cryptocurrencies
                            WHERE is_active = TRUE
                            ORDER BY symbol
                            """)
                results = cur.fetchall()
                logger.debug(f"📋 Загружено из БД: {len(results)} криптовалют")
                return results
        except Exception as e:
            logger.error(f"❌ Ошибка получения списка криптовалют: {e}")
            return []


# Глобальный экземпляр БД
db = Database()