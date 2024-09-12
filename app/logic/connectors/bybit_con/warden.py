import asyncio

import httpx

from app.config import WARDEN_TIMEOUT, logger
from app.database import SecretsORM, Database
from app.logic.utils import AlertWorker
from .client import AsyncClient
from ..abstract import ABCPositionWarden


class BybitWarden(ABCPositionWarden):
    category: str = "linear"

    def __init__(self, db: Database):
        self._db = db
        self._client: AsyncClient | None = None

    async def start_warden(self) -> None:
        """
        Функция запускает бесконечный цикл, в котором проверяются открытые позиции без стопов.
        :return:
        """
        logger.success("Bybit warden started")
        prev_iteration_positions: list[dict] = []

        while True:
            secrets: SecretsORM = await self._db.secrets_repo.get()
            if all([secrets.bybit_api_key, secrets.bybit_api_secret]):
                try:
                    if self._client:
                        await self._client.close_connection()
                    self._client: AsyncClient = await AsyncClient.create(
                        api_key=secrets.bybit_api_key,
                        api_secret=secrets.bybit_api_secret)

                    # Получаем все открытые позиции
                    positions: list[dict] = await self._get_open_positions()

                    # Находим позиции без стопов
                    positions_wo_stop: list[dict] = self._get_positions_wo_stop(positions)
                    if positions_wo_stop:
                        logger.info(f"Find positions w/o stop: {positions_wo_stop}")

                    # Находим одинаковые элементы в двух последних итерациях
                    positions_to_close = self._find_common_elements(
                        prev_iteration=prev_iteration_positions,
                        curr_iteration=positions_wo_stop)
                    if positions_to_close:
                        logger.warning(f"I should close positions: {positions_to_close}")

                    # Обновляем историю найденных позиций
                    prev_iteration_positions = positions_wo_stop

                    # Заркываем позиции
                    await self._close_positions(positions_to_close=positions_to_close)

                except httpx.ConnectTimeout as e:
                    logger.error(f"Error in bybit warden: ConnectTimeout: {e}")
                except Exception as e:
                    logger.exception(f"Error in bybit warden: {e}")
            else:
                prev_iteration_positions.clear()

            await asyncio.sleep(WARDEN_TIMEOUT)

    async def _close_positions(self, positions_to_close: list[dict]) -> None:
        """
        Функиця закрывает позиции и отменяет ордера.
        :param positions_to_close: [{symbol:, positionAmt:}, ...]
        :return:
        """
        for p in positions_to_close:
            responce: dict = await self._client.place_order(
                category=self.category,
                orderType="Market",
                symbol=p["symbol"],
                qty=p["size"],
                side="Buy" if p["side"] == "Sell" else "Sell")
            if responce.get("retMsg") == "OK":
                logger.info(f"Close position w/o stop: {responce}")
                await AlertWorker.warning(
                    f"Позиция по {p['symbol']} размером {p['size']} на bybit.com была закрыта, "
                    f"потому что по ней не стоял стоп.")
            else:
                logger.error(f"Error while closing position w/o stop: {responce}")
                await AlertWorker.error(
                    f"Ошибка при закрытии позиции на bybit.com {positions_to_close}, на "
                    f"которой нет стопа: {responce}")

    def _get_positions_wo_stop(self, positions: list[dict]) -> list[dict]:
        """
        Функция возвращает список позиций без стопов.
        :return:
        """
        positions_wo_stop: list[dict] = []
        for p in positions:
            if not p["stopLoss"]:
                positions_wo_stop.append({"symbol": p["symbol"], "size": p["size"], "side": p["side"]})

        return positions_wo_stop

    async def _get_open_positions(self) -> list[dict]:
        """
        Функция возвращает все открытые позиции на аккаунте.
        Если их нет - возвращает пустой список.
        {'symbol': 'XRPUSDT', 'leverage': '1', 'autoAddMargin': 0, 'avgPrice': '0.4938', 'liqPrice': '',
         'riskLimitValue': '200000', 'takeProfit': '', 'positionValue': '5.4318', 'isReduceOnly': False,
         'tpslMode': 'Full', 'riskId': 41, 'trailingStop': '0', 'unrealisedPnl': '0', 'markPrice': '0.4938',
         'adlRankIndicator': 2, 'cumRealisedPnl': '-0.0054318', 'positionMM': '0.0407385',
         'createdTime': '1681120337632', 'positionIdx': 0, 'positionIM': '5.4318', 'seq': 102431636611,
         'updatedTime': '1717863077442', 'side': 'Buy', 'bustPrice': '', 'positionBalance': '0',
         'leverageSysUpdatedTime': '', 'curRealisedPnl': '-0.0054318', 'size': '11', 'positionStatus': 'Normal',
         'mmrSysUpdatedTime': '', 'stopLoss': '', 'tradeMode': 0, 'sessionAvgPrice': ''}
        """
        responce: dict = await self._client.get_position_info(
            category=self.category,
            settleCoin="USDT")
        return responce["result"]["list"]

    async def _get_open_orders(self) -> list[dict]:
        """
        Функция возвращает все открытые ордера на аккаунте.
        Если их нет - возвращает пустой список.

        {'symbol': 'BTCUSDT', 'orderType': 'Limit', 'orderLinkId': '', 'slLimitPrice': '0',
          'orderId': '68016cc3-99f6-429e-b372-84dcbc5c5dd5', 'cancelType': 'UNKNOWN', 'avgPrice': '',
          'stopOrderType': '', 'lastPriceOnCreated': '69491.7', 'orderStatus': 'New',
          'createType': 'CreateByUser', 'takeProfit': '', 'cumExecValue': '0', 'tpslMode': '',
          'smpType': 'None', 'triggerDirection': 0, 'blockTradeId': '', 'isLeverage': '',
          'rejectReason': 'EC_NoError', 'price': '66482.5', 'orderIv': '',
          'createdTime': '1717861832922', 'tpTriggerBy': '', 'positionIdx': 0, 'timeInForce': 'GTC',
          'leavesValue': '132.965', 'updatedTime': '1717861832923', 'side': 'Buy', 'smpGroup': 0,
          'triggerPrice': '', 'tpLimitPrice': '0', 'cumExecFee': '0', 'leavesQty': '0.002',
          'slTriggerBy': '', 'closeOnTrigger': False, 'placeType': '', 'cumExecQty': '0',
          'reduceOnly': False, 'qty': '0.002', 'stopLoss': '', 'marketUnit': '', 'smpOrderId': '',
          'triggerBy': ''}]

        :return:

        """
        responce: dict = await self._client.get_open_orders(
            category=self.category,
            settleCoin="USDT")
        return responce["result"]["list"]
