#!/usr/bin/env python3
"""
Тест SSL сертификатов для различных криптовалютных API
Запуск: python test_crypto_apis.py
"""

import aiohttp
import asyncio
import ssl
import sys

# Список API для тестирования
CRYPTO_APIS = {
    'CoinGecko': {
        'url': 'https://api.coingecko.com/api/v3/ping',
        'free': True,
        'rate_limit': '10-50 req/min'
    },
    'Binance': {
        'url': 'https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT',
        'free': True,
        'rate_limit': '1200 req/min'
    },
    'CoinMarketCap (Sandbox)': {
        'url': 'https://sandbox-api.coinmarketcap.com/v1/cryptocurrency/listings/latest',
        'free': True,
        'rate_limit': 'Sandbox'
    },
    'CoinMarketCap (Production)': {
        'url': 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest',
        'free': False,
        'rate_limit': '333 req/day (free)'
    },
    'CryptoCompare': {
        'url': 'https://min-api.cryptocompare.com/data/price?fsym=BTC&tsyms=USD',
        'free': True,
        'rate_limit': '100,000 req/month'
    },
    'Coinbase': {
        'url': 'https://api.coinbase.com/v2/exchange-rates?currency=BTC',
        'free': True,
        'rate_limit': '10,000 req/hour'
    },
    'Kraken': {
        'url': 'https://api.kraken.com/0/public/Ticker?pair=XBTUSD',
        'free': True,
        'rate_limit': '1 req/sec'
    },
    'Bitfinex': {
        'url': 'https://api-pub.bitfinex.com/v2/ticker/tBTCUSD',
        'free': True,
        'rate_limit': '90 req/min'
    },
    'KuCoin': {
        'url': 'https://api.kucoin.com/api/v1/market/orderbook/level1?symbol=BTC-USDT',
        'free': True,
        'rate_limit': '100 req/10sec'
    },
    'Bybit': {
        'url': 'https://api.bybit.com/v2/public/tickers?symbol=BTCUSDT',
        'free': True,
        'rate_limit': '50 req/sec'
    },
    'Gate.io': {
        'url': 'https://api.gateio.ws/api/v4/spot/tickers?currency_pair=BTC_USDT',
        'free': True,
        'rate_limit': '900 req/sec'
    },
    'Messari': {
        'url': 'https://data.messari.io/api/v1/assets/bitcoin/metrics',
        'free': True,
        'rate_limit': '20 req/min'
    },
}


async def test_api_ssl(name, info, use_ssl_verify=True):
    """Тестирует API с проверкой SSL"""
    result = {
        'name': name,
        'url': info['url'],
        'ssl_works': False,
        'status': None,
        'error': None,
        'free': info['free'],
        'rate_limit': info['rate_limit']
    }

    try:
        # Создаем SSL контекст
        if use_ssl_verify:
            try:
                import certifi
                ssl_context = ssl.create_default_context(cafile=certifi.where())
            except ImportError:
                ssl_context = ssl.create_default_context()
        else:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

        connector = aiohttp.TCPConnector(ssl=ssl_context)
        timeout = aiohttp.ClientTimeout(total=10)

        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            async with session.get(info['url']) as response:
                result['status'] = response.status
                result['ssl_works'] = True

    except ssl.SSLError as e:
        result['error'] = f"SSL Error: {str(e)}"
    except aiohttp.ClientConnectorCertificateError as e:
        result['error'] = f"Certificate Error: {str(e)}"
    except asyncio.TimeoutError:
        result['error'] = "Timeout"
    except Exception as e:
        result['error'] = f"{type(e).__name__}: {str(e)}"

    return result


async def test_all_apis():
    """Тестирует все API"""
    print("=" * 80)
    print("🔐 ТЕСТ SSL СЕРТИФИКАТОВ ДЛЯ КРИПТОВАЛЮТНЫХ API")
    print("=" * 80)
    print(f"Python: {sys.version}")
    print(f"SSL: {ssl.OPENSSL_VERSION}")

    try:
        import certifi
        print(f"Certifi: ✅ {certifi.where()}")
    except ImportError:
        print("Certifi: ❌ НЕ УСТАНОВЛЕН")

    print("=" * 80)
    print()

    # Тест с проверкой SSL
    print("📊 ТЕСТИРОВАНИЕ С ПРОВЕРКОЙ SSL СЕРТИФИКАТОВ")
    print("-" * 80)

    tasks = [test_api_ssl(name, info, use_ssl_verify=True)
             for name, info in CRYPTO_APIS.items()]
    results = await asyncio.gather(*tasks)

    # Результаты
    working_apis = []
    broken_apis = []

    for result in results:
        status_icon = "✅" if result['ssl_works'] else "❌"
        free_icon = "🆓" if result['free'] else "💰"

        print(f"\n{status_icon} {free_icon} {result['name']}")
        print(f"   URL: {result['url']}")
        print(f"   Rate Limit: {result['rate_limit']}")

        if result['ssl_works']:
            print(f"   Status: HTTP {result['status']}")
            working_apis.append(result)
        else:
            print(f"   Error: {result['error']}")
            broken_apis.append(result)

    # Итоги
    print("\n" + "=" * 80)
    print("📈 ИТОГИ")
    print("=" * 80)

    print(f"\n✅ РАБОТАЮТ БЕЗ ПРОБЛЕМ С SSL ({len(working_apis)}):")
    for api in working_apis:
        free_text = "FREE" if api['free'] else "PAID"
        print(f"   • {api['name']} ({free_text}) - {api['rate_limit']}")

    print(f"\n❌ ТРЕБУЮТ ОБХОДА SSL ({len(broken_apis)}):")
    for api in broken_apis:
        print(f"   • {api['name']}")

    # Рекомендации
    print("\n" + "=" * 80)
    print("💡 РЕКОМЕНДАЦИИ")
    print("=" * 80)

    if working_apis:
        print("\n🎯 Лучшие варианты для использования:")

        # Сортируем по бесплатности и rate limit
        best_apis = sorted(working_apis,
                           key=lambda x: (not x['free'], x['name']))

        for i, api in enumerate(best_apis[:3], 1):
            print(f"\n{i}. {api['name']}")
            print(f"   Free: {'Да' if api['free'] else 'Нет'}")
            print(f"   Rate Limit: {api['rate_limit']}")
            print(f"   SSL: Работает без проблем ✅")

    if broken_apis:
        print(f"\n⚠️  Для использования следующих API нужно:")
        print(f"   1. Установить сертификаты: /Applications/Python 3.13/Install Certificates.command")
        print(f"   2. Или использовать обход SSL (не рекомендуется)")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(test_all_apis())