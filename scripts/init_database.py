#!/usr/bin/env python3
"""
Скрипт для инициализации базы данных с популярными криптовалютами
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models.database import db


def init_popular_cryptos():
    """Добавление популярных криптовалют в базу данных"""

    popular_cryptos = [
        # Основные криптовалюты
        {'id': 'BTC', 'symbol': 'BTC', 'name': 'Bitcoin'},
        {'id': 'ETH', 'symbol': 'ETH', 'name': 'Ethereum'},
        {'id': 'BNB', 'symbol': 'BNB', 'name': 'Binance Coin'},
        {'id': 'SOL', 'symbol': 'SOL', 'name': 'Solana'},
        {'id': 'XRP', 'symbol': 'XRP', 'name': 'Ripple'},

        # Популярные альткойны
        {'id': 'ADA', 'symbol': 'ADA', 'name': 'Cardano'},
        {'id': 'DOGE', 'symbol': 'DOGE', 'name': 'Dogecoin'},
        {'id': 'DOT', 'symbol': 'DOT', 'name': 'Polkadot'},
        {'id': 'LTC', 'symbol': 'LTC', 'name': 'Litecoin'},
        {'id': 'MATIC', 'symbol': 'MATIC', 'name': 'Polygon'},

        # Дополнительные
        {'id': 'AVAX', 'symbol': 'AVAX', 'name': 'Avalanche'},
        {'id': 'LINK', 'symbol': 'LINK', 'name': 'Chainlink'},
        {'id': 'ATOM', 'symbol': 'ATOM', 'name': 'Cosmos'},
        {'id': 'UNI', 'symbol': 'UNI', 'name': 'Uniswap'},
        {'id': 'XLM', 'symbol': 'XLM', 'name': 'Stellar'},
    ]

    print("🔄 Инициализация базы данных...")

    for crypto in popular_cryptos:
        db.add_cryptocurrency(crypto['id'], crypto['symbol'], crypto['name'])
        print(f"✅ Добавлена: {crypto['symbol']} - {crypto['name']}")

    print("🎯 База данных инициализирована!")


if __name__ == '__main__':
    init_popular_cryptos()