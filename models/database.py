import psycopg2
from psycopg2.extras import RealDictCursor
import os
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class Database:
    def __init__(self):
        self.conn = None
        self.connect()

    def connect(self):
        """Подключение к PostgreSQL"""
        try:
            self.conn = psycopg2.connect(
                host=os.getenv('DB_HOST', 'localhost'),
                database=os.getenv('DB_NAME', 'cryptobot'),
                user=os.getenv('DB_USER', 'postgres'),
                password=os.getenv('DB_PASSWORD', 'password'),
                port=os.getenv('DB_PORT', '5432')
            )
            self.create_tables()
            logger.info("✅ Подключение к PostgreSQL установлено")
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к БД: {e}")
            raise

    def create_tables(self):
        """Создание таблиц"""
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

            # Таблица для кэша поиска
            cur.execute("""
                        CREATE TABLE IF NOT EXISTS search_cache
                        (
                            id
                            SERIAL
                            PRIMARY
                            KEY,
                            query
                            VARCHAR
                        (
                            100
                        ) NOT NULL,
                            results JSONB,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                            )
                        """)

            # Индексы для быстрого поиска
            cur.execute("""
                        CREATE INDEX IF NOT EXISTS idx_crypto_symbol ON cryptocurrencies(symbol);
                        """)
            cur.execute("""
                        CREATE INDEX IF NOT EXISTS idx_crypto_name ON cryptocurrencies(name);
                        """)

            self.conn.commit()

    def search_cryptocurrencies(self, query):
        """Поиск криптовалют в БД"""
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

                return cur.fetchall()
        except Exception as e:
            logger.error(f"❌ Ошибка поиска в БД: {e}")
            return []

    def add_cryptocurrency(self, coinbase_id, symbol, name):
        """Добавление криптовалюты в БД"""
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
                return True
        except Exception as e:
            logger.error(f"❌ Ошибка добавления криптовалюты: {e}")
            self.conn.rollback()
            return False

    def get_all_cryptocurrencies(self):
        """Получение всех криптовалют"""
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                            SELECT coinbase_id, symbol, name
                            FROM cryptocurrencies
                            WHERE is_active = TRUE
                            ORDER BY symbol
                            """)
                return cur.fetchall()
        except Exception as e:
            logger.error(f"❌ Ошибка получения списка криптовалют: {e}")
            return []


# Глобальный экземпляр БД
db = Database()