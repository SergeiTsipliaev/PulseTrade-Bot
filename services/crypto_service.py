# import aiohttp
# import asyncio
# import time
# import hmac
# import hashlib
# from urllib.parse import urlencode
# from typing import Dict, Any, Optional, List
# import json
# import ssl
#
# from config import BybitConfig
#
#
# class BybitService:
#     def __init__(self, api_key: str = None, api_secret: str = None):
#         self.api_key = api_key or BybitConfig.API_KEY
#         self.api_secret = api_secret or BybitConfig.API_SECRET
#         self.base_url = BybitConfig.BASE_URL
#         # Создаем кастомный SSL контекст
#         self.ssl_context = ssl.create_default_context()
#         self.ssl_context.check_hostname = False
#         self.ssl_context.verify_mode = ssl.CERT_NONE
#
#     async def _make_request(self, endpoint: str, params: Dict[str, Any] = None, private: bool = False) -> Dict[
#         str, Any]:
#         """Упрощенный метод для выполнения запросов"""
#         if params is None:
#             params = {}
#
#         url = f"{self.base_url}{endpoint}"
#
#         # Для публичных запросов добавляем параметры в URL
#         if not private and params:
#             url += "?" + urlencode(params)
#             params = {}
#
#         headers = {"Content-Type": "application/json"}
#
#         if private:
#             timestamp = str(int(time.time() * 1000))
#             recv_window = "5000"
#
#             param_str = timestamp + self.api_key + recv_window + urlencode(params)
#             signature = hmac.new(
#                 bytes(self.api_secret, "utf-8"),
#                 param_str.encode("utf-8"),
#                 hashlib.sha256
#             ).hexdigest()
#
#             headers.update({
#                 "X-BAPI-API-KEY": self.api_key,
#                 "X-BAPI-TIMESTAMP": timestamp,
#                 "X-BAPI-RECV-WINDOW": recv_window,
#                 "X-BAPI-SIGN": signature
#             })
#
#         # Используем кастомный SSL контекст
#         connector = aiohttp.TCPConnector(ssl=self.ssl_context)
#
#         async with aiohttp.ClientSession(connector=connector) as session:
#             try:
#                 if private:
#                     async with session.post(url, json=params, headers=headers) as response:
#                         data = await response.json()
#                 else:
#                     async with session.get(url, headers=headers) as response:
#                         data = await response.json()
#
#                 if data.get("retCode") != 0:
#                     return {"error": f"API error: {data.get('retMsg', 'Unknown error')}"}
#                 return data
#
#             except Exception as e:
#                 return {"error": f"Request failed: {str(e)}"}