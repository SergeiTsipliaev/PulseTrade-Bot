import aiohttp
import asyncio
import time
import hmac
import hashlib
from urllib.parse import urlencode
from typing import Dict, Any, Optional, List
import json

from config import BybitConfig


class BybitService:
    def __init__(self, api_key: str = None, api_secret: str = None):
        self.api_key = api_key or BybitConfig.API_KEY
        self.api_secret = api_secret or BybitConfig.API_SECRET
        self.base_url = BybitConfig.BASE_URL
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def _generate_signature(self, params: Dict[str, Any]) -> tuple:
        """Генерация подписи для запросов"""
        timestamp = str(int(time.time() * 1000))
        recv_window = "5000"

        param_str = timestamp + self.api_key + recv_window + urlencode(params)
        signature = hmac.new(
            bytes(self.api_secret, "utf-8"),
            param_str.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        return timestamp, recv_window, signature

    async def _request(self, method: str, endpoint: str, params: Dict[str, Any] = None, private: bool = False) -> Dict[
        str, Any]:
        """Базовый метод для выполнения запросов"""
        if params is None:
            params = {}

        url = f"{self.base_url}{endpoint}"
        headers = {"Content-Type": "application/json"}

        if private:
            timestamp, recv_window, signature = self._generate_signature(params)
            headers.update({
                "X-BAPI-API-KEY": self.api_key,
                "X-BAPI-TIMESTAMP": timestamp,
                "X-BAPI-RECV-WINDOW": recv_window,
                "X-BAPI-SIGN": signature
            })

        async with self.session.request(method, url, json=params, headers=headers) as response:
            data = await response.json()
            if data.get("retCode") != 0:
                raise Exception(f"Bybit API error: {data.get('retMsg', 'Unknown error')}")
            return data

    # Market Data Methods
    async def search_symbols(self, query: str) -> List[Dict[str, Any]]:
        """Поиск торговых пар"""
        data = await self._request("GET", "/v5/market/instruments-info", {"category": "spot"})
        results = []
        query = query.upper()

        for symbol_data in data["result"]["list"]:
            symbol = symbol_data["symbol"]
            if query in symbol:
                results.append({
                    "symbol": symbol,
                    "base_coin": symbol_data["baseCoin"],
                    "quote_coin": symbol_data["quoteCoin"],
                    "min_order_qty": float(symbol_data.get("lotSizeFilter", {}).get("minOrderQty", 0)),
                    "max_order_qty": float(symbol_data.get("lotSizeFilter", {}).get("maxOrderQty", 0)),
                    "price_scale": int(symbol_data.get("priceScale", 8))
                })

        return results[:10]  # Ограничиваем результаты

    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """Получение данных тикера"""
        if not symbol.endswith('USDT'):
            symbol = f"{symbol}USDT"

        data = await self._request("GET", "/v5/market/tickers", {"category": "spot", "symbol": symbol})
        ticker = data["result"]["list"][0]

        return {
            "symbol": ticker["symbol"],
            "last_price": float(ticker["lastPrice"]),
            "bid_price": float(ticker["bid1Price"]),
            "ask_price": float(ticker["ask1Price"]),
            "volume_24h": float(ticker["volume24h"]),
            "price_change_24h": float(ticker["price24hPcnt"]),
            "price_change_percent_24h": float(ticker["price24hPcnt"]) * 100
        }

    async def get_klines(self, symbol: str, interval: str = "60", limit: int = 500) -> List[float]:
        """Получение исторических данных для LSTM"""
        if not symbol.endswith('USDT'):
            symbol = f"{symbol}USDT"

        data = await self._request("GET", "/v5/market/kline", {
            "category": "spot",
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        })

        # Извлекаем цены закрытия
        prices = [float(candle[4]) for candle in data["result"]["list"]]  # close price
        return prices[::-1]  # reverse to chronological order

    # Trading Methods
    async def get_wallet_balance(self, coin: str = None) -> Dict[str, Any]:
        """Получение баланса кошелька"""
        params = {"accountType": "UNIFIED"}
        if coin:
            params["coin"] = coin
        return await self._request("GET", "/v5/account/wallet-balance", params, private=True)

    async def place_order(self, symbol: str, side: str, quantity: float, order_type: str = "Market",
                          price: float = None) -> Dict[str, Any]:
        """Размещение ордера"""
        params = {
            "category": "spot",
            "symbol": symbol,
            "side": side,
            "orderType": order_type,
            "qty": str(quantity),
            "timeInForce": "GTC"
        }

        if price and order_type == "Limit":
            params["price"] = str(price)

        return await self._request("POST", "/v5/order/create", params, private=True)