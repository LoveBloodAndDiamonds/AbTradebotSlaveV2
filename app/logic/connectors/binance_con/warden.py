import asyncio

from binance import AsyncClient
from binance.enums import *

from app.config import WARDEN_TIMEOUT, logger
from app.database import SecretsORM, Database
from app.logic.utils import AlertWorker
from ..abstract import ABCPositionWarden


class BinanceWarden(ABCPositionWarden):

    def __init__(self, db: Database):
        self._db = db
        self._client: AsyncClient | None = None

    async def start_warden(self) -> None:
        """
        Функция запускает бесконечный цикл, в котором проверяются открытые позиции без стопов.
        :return:
        """
        logger.success("Binance warden started")
        prev_iteration_positions: list[dict] = []

        while True:
            secrets: SecretsORM = await self._db.secrets_repo.get()
            if all([secrets.binance_api_secret, secrets.binance_api_key]):
                try:
                    if self._client:
                        await self._client.close_connection()
                    self._client: AsyncClient = await AsyncClient.create(
                        api_key=secrets.binance_api_key,
                        api_secret=secrets.binance_api_secret)
                    orders: list[dict] = await self._get_open_orders()  # Получаем все открытые ордера
                    positions: list[dict] = await self._get_open_positions()  # Получаем все открытые позиции

                    # Получаем позиции, которые нужно закрыть
                    curr_iteration_positions: list[dict] = self._check_positions_health(
                        orders=orders,
                        positions=positions)
                    if curr_iteration_positions:
                        logger.info(f"Find positions to w/o stop: {curr_iteration_positions}")

                    # Получаем позиции, которые совпали с прошлой итерацией (подтверждение на закрытие)
                    positions_to_close: list[dict] = self._find_common_elements(
                        curr_iteration=curr_iteration_positions,
                        prev_iteration=prev_iteration_positions)
                    if positions_to_close:
                        logger.warning(f"I should close positions: {positions_to_close}")

                    # Обновляем историю найденных позиций
                    prev_iteration_positions = curr_iteration_positions

                    # Закрываем все позиции, которые нужны закрыть
                    await self._close_positions(positions_to_close)

                except Exception as e:
                    logger.error(f"Error in binance warden: {e}")
            else:
                prev_iteration_positions.clear()

            await asyncio.sleep(WARDEN_TIMEOUT)

    def _check_positions_health(
            self,
            positions: list[dict],
            orders: list[dict]
    ) -> list[dict]:
        """
        Функция проверяет, чтобы на позиции обязательно стоял стоп-ордер.
        Возвращает список позииций, в которых стоп ордер не стоит.
        :param positions:
        :param orders:
        :return:
        """
        positions_to_close: list[dict] = []

        symbol_orders_types: dict[str, list[dict]] = {}
        for order in orders:
            if order["symbol"] not in symbol_orders_types:
                symbol_orders_types[order["symbol"]] = [order["type"]]
            else:
                symbol_orders_types[order["symbol"]].append(order["type"])

        for position in positions:
            # Проверка хотя бы какого-нибудь ордера на позиции, если ордеров совсем нет -
            # то такую позицию надо закрыть
            if position["symbol"] not in symbol_orders_types:
                positions_to_close.append(position)
                continue

            # Проверка типа ордеров
            position_orders_types: list[dict] = symbol_orders_types[position["symbol"]]
            for order_type in position_orders_types:
                if order_type in [FUTURE_ORDER_TYPE_STOP_MARKET, FUTURE_ORDER_TYPE_STOP]:
                    break
            else:
                positions_to_close.append(position)

        return positions_to_close

    async def _get_open_orders(self) -> list[dict]:
        """
        Функция возвращает все открытые ордера на аккаунте.
        Если их нет - возвращает пустой список.
        Weight = 40
        :return: [
              {
                "avgPrice": "0.00000",
                "clientOrderId": "abc",
                "cumQuote": "0",
                "executedQty": "0",
                "orderId": 1917641,
                "origQty": "0.40",
                "origType": "TRAILING_STOP_MARKET",
                "price": "0",
                "reduceOnly": false,
                "side": "BUY",
                "positionSide": "SHORT",
                "status": "NEW",
                "stopPrice": "9300",                // please ignore when order type is TRAILING_STOP_MARKET
                "closePosition": false,   // if Close-All
                "symbol": "BTCUSDT",
                "time": 1579276756075,              // order time
                "timeInForce": "GTC",
                "type": "TRAILING_STOP_MARKET",
                "activatePrice": "9020",            // activation price, only return with TRAILING_STOP_MARKET order
                "priceRate": "0.3",                 // callback rate, only return with TRAILING_STOP_MARKET order
                "updateTime": 1579276756075,        // update time
                "workingType": "CONTRACT_PRICE",
                "priceProtect": false,            // if conditional order trigger is protected
                "priceMatch": "NONE",              //price match mode
                "selfTradePreventionMode": "NONE", //self trading preventation mode
                "goodTillDate": 0      //order pre-set auot cancel time for TIF GTD order
              }
            ]

        """
        return await self._client.futures_get_open_orders()

    async def _get_open_positions(self) -> list[dict]:
        """
        Функция возвращает все открытые позиции на аккаунте.
        Если их нет - возвращает пустой список.
        Weight = 5
        :return:[
            // only "BOTH" positions will be returned with One-way mode
            // only "LONG" and "SHORT" positions will be returned with Hedge mode
            {
                "symbol": "BTCUSDT",    // symbol name
                "initialMargin": "0",   // initial margin required with current mark price
                "maintMargin": "0",     // maintenance margin required
                "unrealizedProfit": "0.00000000",  // unrealized profit
                "positionInitialMargin": "0",      // initial margin required for positions with current mark price
                "openOrderInitialMargin": "0",     // initial margin required for open orders with current mark price
                "leverage": "100",      // current initial leverage
                "isolated": true,       // if the position is isolated
                "entryPrice": "0.00000",    // average entry price
                "maxNotional": "250000",    // maximum available notional with current leverage
                "bidNotional": "0",  // bids notional, ignore
                "askNotional": "0",  // ask notional, ignore
                "positionSide": "BOTH",     // position side
                "positionAmt": "0",         // position amount
                "updateTime": 0           // last update time
            }
        ]
        """
        open_positions: list[dict] = []

        account_info: dict = await self._client.futures_account()
        for position in account_info["positions"]:
            # Проверка на размер позиции
            if float(position["positionAmt"]) != 0:
                open_positions.append(
                    {
                        "symbol": position["symbol"],
                        "positionAmt": float(position["positionAmt"]),
                    }
                )
        return open_positions

    async def _close_positions(self, positions_to_close: list[dict]) -> None:
        """
        Функиця закрывает позиции и отменяет ордера.
        :param positions_to_close: [{symbol:, positionAmt:}, ...]
        :return:
        """
        for position in positions_to_close:
            responce: dict = await self._client.futures_create_order(
                symbol=position["symbol"],
                type=FUTURE_ORDER_TYPE_MARKET,
                quantity=abs(position["positionAmt"]),
                side=SIDE_BUY if position["positionAmt"] < 0 else SIDE_SELL,
                reduceOnly=True
            )
            if responce.get("status", None) == "NEW":
                logger.info(f"Close position w/o stop: {responce}")
                await AlertWorker.warning(
                    f"Позиция по {position['symbol']} на binance.com размером {position['positionAmt']} "
                    f"была закрыта, потому что по ней не стоял стоп.")
            else:
                logger.error(f"Error while closing position w/o stop: {responce}")
                await AlertWorker.error(
                    f"Ошибка при закрытии позиции на binance.com {positions_to_close}, "
                    f"на которой нет стопа: {responce}")
