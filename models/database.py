import psycopg2
from psycopg2.extras import RealDictCursor
import asyncio
import logging
import os
from contextlib import contextmanager
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class Database:
    """Асинхронный класс для работы с PostgreSQL"""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.conn = None
        self.is_connected = False

    def connect(self) -> bool:
        """Синхронное подключение к БД"""
        try:
            self.conn = psycopg2.connect(self.connection_string, connect_timeout=5)
            self.is_connected = True
            self.create_tables()
            logger.info("✅ PostgreSQL подключение установлено")
            return True
        except psycopg2.OperationalError as e:
            logger.error(f"❌ Ошибка подключения PostgreSQL: {e}")
            self.is_connected = False
            return False
        except Exception as e:
            logger.error(f"❌ Неожиданная ошибка подключения: {e}")
            self.is_connected = False
            return False

    def reconnect(self) -> bool:
        """Переподключение к БД"""
        try:
            if self.conn:
                self.conn.close()
        except:
            pass
        return self.connect()

    @contextmanager
    def get_cursor(self):
        """Context manager для получения курсора"""
        cursor = None
        try:
            if not self.is_connected:
                self.reconnect()
            cursor = self.conn.cursor(cursor_factory=RealDictCursor)
            yield cursor
            self.conn.commit()
        except Exception as e:
            if self.conn:
                self.conn.rollback()
            logger.error(f"❌ Ошибка БД: {e}")
            raise
        finally:
            if cursor:
                cursor.close()

    def create_tables(self):
        """Создание таблиц если их нет"""
        try:
            with self.get_cursor() as cur:
                # Таблица криптовалют
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS cryptocurrencies (
                        id SERIAL PRIMARY KEY,
                        symbol VARCHAR(20) UNIQUE NOT NULL,
                        name VARCHAR(100) NOT NULL,
                        display_name VARCHAR(10),
                        emoji VARCHAR(5),
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Таблица цен для кэширования
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS price_history (
                        id SERIAL PRIMARY KEY,
                        symbol VARCHAR(20) NOT NULL,
                        price DECIMAL(20, 8) NOT NULL,
                        change_24h DECIMAL(10, 2),
                        volume_24h DECIMAL(20, 2),
                        high_24h DECIMAL(20, 8),
                        low_24h DECIMAL(20, 8),
                        timestamp TIMESTAMP NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (symbol) REFERENCES cryptocurrencies(symbol) ON DELETE CASCADE
                    )
                """)

                # Индексы для оптимизации
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_crypto_symbol 
                    ON cryptocurrencies(symbol)
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_price_history_symbol 
                    ON price_history(symbol)
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_price_history_timestamp 
                    ON price_history(timestamp DESC)
                """)

                logger.info("✅ Таблицы БД созданы/проверены")
        except Exception as e:
            logger.error(f"❌ Ошибка создания таблиц: {e}")

    def search_cryptocurrencies(self, query: str) -> List[Dict]:
        """Поиск криптовалют в БД"""
        if not self.is_connected:
            logger.debug("🔍 Поиск: БД недоступна")
            return []

        try:
            with self.get_cursor() as cur:
                query_param = f"{query.upper()}%"
                cur.execute("""
                    SELECT symbol, name, display_name, emoji
                    FROM cryptocurrencies
                    WHERE (UPPER(symbol) LIKE %s OR UPPER(name) LIKE %s)
                    AND is_active = TRUE
                    ORDER BY 
                        CASE 
                            WHEN UPPER(symbol) = %s THEN 1
                            WHEN UPPER(symbol) LIKE %s THEN 2
                            ELSE 3
                        END,
                        symbol
                    LIMIT 20
                """, (query_param, f"%{query.upper()}%", query.upper(), query_param))

                results = cur.fetchall()
                logger.debug(f"🔍 Найдено в БД: {len(results)} результатов для '{query}'")
                return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"❌ Ошибка поиска: {e}")
            return []

    def add_cryptocurrency(self, symbol: str, name: str, display_name: str, emoji: str = "") -> bool:
        """Добавление криптовалюты в БД"""
        if not self.is_connected:
            logger.debug(f"💾 Пропускаем сохранение {symbol} - БД недоступна")
            return False

        try:
            with self.get_cursor() as cur:
                cur.execute("""
                    INSERT INTO cryptocurrencies (symbol, name, display_name, emoji)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (symbol) 
                    DO UPDATE SET 
                        name = EXCLUDED.name,
                        display_name = EXCLUDED.display_name,
                        emoji = EXCLUDED.emoji,
                        updated_at = CURRENT_TIMESTAMP
                """, (symbol, name, display_name, emoji))
                logger.debug(f"💾 Сохранена криптовалюта: {symbol}")
                return True
        except Exception as e:
            logger.error(f"❌ Ошибка добавления: {e}")
            return False

    def get_all_cryptocurrencies(self) -> List[Dict]:
        """Получение всех активных криптовалют"""
        if not self.is_connected:
            logger.debug("📋 Получение списка: БД недоступна")
            return []

        try:
            with self.get_cursor() as cur:
                cur.execute("""
                    SELECT symbol, name, display_name, emoji
                    FROM cryptocurrencies
                    WHERE is_active = TRUE
                    ORDER BY symbol
                """)
                results = cur.fetchall()
                logger.debug(f"📋 Загружено: {len(results)} криптовалют")
                return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"❌ Ошибка получения списка: {e}")
            return []

    def cache_price_history(self, symbol: str, price: float, change_24h: float,
                           volume_24h: float, high_24h: float, low_24h: float) -> bool:
        """Кэширование истории цен"""
        if not self.is_connected:
            return False

        try:
            with self.get_cursor() as cur:
                cur.execute("""
                    INSERT INTO price_history 
                    (symbol, price, change_24h, volume_24h, high_24h, low_24h, timestamp)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                """, (symbol, price, change_24h, volume_24h, high_24h, low_24h))
                return True
        except Exception as e:
            logger.error(f"❌ Ошибка кэширования: {e}")
            return False

    def get_price_history(self, symbol: str, limit: int = 100) -> List[Dict]:
        """Получение истории цен из кэша"""
        if not self.is_connected:
            return []

        try:
            with self.get_cursor() as cur:
                cur.execute("""
                    SELECT price, change_24h, volume_24h, high_24h, low_24h, timestamp
                    FROM price_history
                    WHERE symbol = %s
                    ORDER BY timestamp DESC
                    LIMIT %s
                """, (symbol, limit))
                results = cur.fetchall()
                return [dict(row) for row in reversed(results)]
        except Exception as e:
            logger.error(f"❌ Ошибка получения истории: {e}")
            return []

    def close(self):
        """Закрытие соединения"""
        try:
            if self.conn:
                self.conn.close()
                self.is_connected = False
                logger.info("✅ БД соединение закрыто")
        except Exception as e:
            logger.error(f"❌ Ошибка закрытия: {e}")


# Глобальный экземпляр БД
try:
    from config import DATABASE_URL
    db = Database(DATABASE_URL)
    db.connect()
except Exception as e:
    logger.error(f"❌ Ошибка инициализации БД: {e}")
    db = None