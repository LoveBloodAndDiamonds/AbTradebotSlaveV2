import base64
import hmac
import json
from datetime import datetime
from typing import Optional, Union, Dict, Any, Literal
from urllib.parse import urlencode

import aiohttp


class BaseClient:
    """
    The base class for all section classes.

    Attributes:
        entrypoint_url (str): an entrypoint URL.

    """
    entrypoint_url: str = "https://www.okx.com"

    def __init__(self, api_key: str, secret_key: str, passphrase: str) -> None:
        """
        Initialize the class.

        """
        self.__api_key = api_key
        self.__secret_key = secret_key
        self.__passphrase = passphrase

    @staticmethod
    async def get_timestamp() -> str:
        """
        Get the current timestamp.

        Returns:
            str: the current timestamp.

        """
        return datetime.utcnow().isoformat(timespec='milliseconds') + 'Z'

    async def generate_sign(self, timestamp: str, method: str, request_path: str, body: Union[dict, str]) -> bytes:
        """
        Generate signed message.

        Args:
            timestamp (str): the current timestamp.
            method (str): the request method is either GET or POST.
            request_path (str): the path of requesting an endpoint.
            body (Union[dict, str]): POST request parameters.

        Returns:
            bytes: the signed message.

        """
        if not body:
            body = ''

        if isinstance(body, dict):
            body = json.dumps(body)

        key = bytes(self.__secret_key, encoding='utf-8')
        msg = bytes(timestamp + method + request_path + body, encoding='utf-8')
        return base64.b64encode(hmac.new(key, msg, digestmod='sha256').digest())

    async def make_request(
            self, method: Literal["GET", "POST"], request_path: str, body: Optional[dict] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Make a request to the OKX API.

        Args:
            method (str): the request method is either GET or POST.
            request_path (str): the path of requesting an endpoint.
            body (Optional[dict]): request parameters. (None)

        Returns:
            Optional[Dict[str, Any]]: the request response.

        """
        timestamp = await self.get_timestamp()
        method = method.upper()
        body = body if body else {}
        if method == "GET" and body:
            request_path += f'?{urlencode(query=body)}'
            body = {}

        sign_msg = await self.generate_sign(timestamp=timestamp, method=method, request_path=request_path, body=body)
        url = self.entrypoint_url + request_path
        header = {
            'Content-Type': 'application/json',
            'OK-ACCESS-KEY': self.__api_key,
            'OK-ACCESS-SIGN': sign_msg.decode(),
            'OK-ACCESS-TIMESTAMP': timestamp,
            'OK-ACCESS-PASSPHRASE': self.__passphrase
        }

        if method == "POST":
            async with aiohttp.ClientSession() as session:
                response = await session.post(
                    url=url,
                    headers=header,
                    data=json.dumps(body) if isinstance(body, dict) else body
                )
            response = await response.json()

        else:
            async with aiohttp.ClientSession() as session:
                response = await session.get(url=url, headers=header)
            response = await response.json()

        if int(response.get('code')):
            raise ConnectionError(f"{response}")

        return response


class AsyncClient(BaseClient):

    def __init__(self, api_key: str, secret_key: str, passphrase: str) -> None:
        super().__init__(api_key, secret_key, passphrase)

    async def _post(self, request_path: str, body: Optional[dict] | str = None) -> Optional[Dict[str, Any]]:
        return await self.make_request("POST", request_path, body)

    async def _get(self, request_path: str, body: Optional[dict] | str = None) -> Optional[Dict[str, Any]]:
        return await self.make_request("GET", request_path, body)

    async def get_account_config(self):
        return await self._get("/api/v5/account/config")

    async def cancel_all_open_orders(
            self,
            instId: str,  # noqa
            ordId: Optional[str] = None,  # noqa
            clOrdId: Optional[str] = None  # noqa
    ) -> Optional[Dict[str, Any]]:
        """
        https://www.okx.com/docs-v5/en/#order-book-trading-trade-post-cancel-multiple-orders
        :param instId:
        :param ordId:
        :param clOrdId:
        :return:
        """
        orders: dict = await self.get_open_orders(dict(instId=instId))
        orders: list[dict] = [o for o in orders["data"]]
        if orders:
            ids: list[str] = [o["ordId"] for o in orders]
            orders_with_ids: list[dict] = [{"instId": instId, "ordId": _id} for _id in ids]
            orders_with_ids: str = json.dumps(orders_with_ids)

            return await self._post("/api/v5/trade/cancel-batch-orders", body=orders_with_ids)
        else:
            return {}

    async def get_open_positions(self, instId: str = None, instType: Literal["SWAP"] = None) -> Optional[Dict[str, Any]]:  # noqa
        body = {}
        if instId:
            body["instId"] = instId
        if instType:
            body["instType"] = instType
        return await self._get("/api/v5/account/positions", body=body)

    async def get_account_positions_risk(self, instType: Literal["SWAP"]) -> Optional[Dict[str, Any]]:  # noqa
        return await self._get("/api/v5/account/account-position-risk", body={"instType": instType})

    async def get_last_price(self, instId: str = None) -> Optional[Dict[str, Any]]:  # noqa
        return await self._get("/api/v5/market/ticker", body={"instId": instId})

    async def get_open_orders(self, body: dict) -> Optional[Dict[str, Any]]:  # noqa
        """
        Получает все открытые ордера для заданного инструмента.

        :return: Словарь с информацией о открытых ордерах или None, если ордера отсутствуют.
        """
        return await self._get("/api/v5/trade/orders-pending", body=body)

    async def place_order(self, body: dict[str, Any]) -> Optional[Dict[str, Any]]:
        return await self._post("/api/v5/trade/order", body=json.dumps(body))

    async def get_open_algo_orders(self, ordType: str = "conditional") -> Optional[Dict[str, Any]]:  # noqa
        """
        Получает все открытые АЛГО ордера.
        :param ordType:
        :return:
        """
        return await self._get("/api/v5/trade/orders-algo-pending", body=dict(ordType=ordType))

    async def close_position(self, body: dict) -> Optional[Dict[str, Any]]:
        return await self._post("/api/v5/trade/close-position", body=body)

    async def place_algo_order(self, body: dict) -> Optional[Dict[str, Any]]:
        return await self._post("/api/v5/trade/order-algo", body=body)
