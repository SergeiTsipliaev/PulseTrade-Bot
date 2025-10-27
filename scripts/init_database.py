#!/usr/bin/env python3
"""
Скрипт инициализации БД с популярными криптовалютами
Используется при первом запуске
"""

import sys
import os
import logging

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from config import POPULAR_CRYPTOS, DATABASE_URL
from models.database import Database

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def init_database():
    """Инициализация БД и загрузка популярных криптовалют"""

    print("\n" + "=" * 70)
    print("🗄️  ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ")
    print("=" * 70 + "\n")

    try:
        # Подключаемся к БД
        db = Database(DATABASE_URL)

        if not db.is_connected:
            print("❌ Не удалось подключиться к БД")
            print(f"   Строка подключения: {DATABASE_URL}")
            return False

        print("✅ Подключение к БД установлено\n")

        # Добавляем популярные криптовалюты
        print("📝 Добавление популярных криптовалют:\n")

        for crypto in POPULAR_CRYPTOS:
            db.add_cryptocurrency(
                symbol=crypto['symbol'],
                name=crypto['name'],
                display_name=crypto['display_name'],
                emoji=crypto['emoji']
            )
            print(f"   ✅ {crypto['symbol']:10} - {crypto['name']:20} {crypto['emoji']}")

        print(f"\n✅ Загружено {len(POPULAR_CRYPTOS)} криптовалют")

        # Получаем и выводим все криптовалюты
        all_cryptos = db.get_all_cryptocurrencies()
        print(f"\n📋 Всего криптовалют в БД: {len(all_cryptos)}\n")

        db.close()

        print("=" * 70)
        print("✅ ИНИЦИАЛИЗАЦИЯ УСПЕШНО ЗАВЕРШЕНА")
        print("=" * 70 + "\n")

        return True

    except Exception as e:
        print(f"❌ Ошибка: {e}\n")
        return False


if __name__ == '__main__':
    success = init_database()
    sys.exit(0 if success else 1)