import json
from typing import Optional

from binance import AsyncClient
from binance.enums import *

from app.config import log_args, logger
from app.logic.utils import AlertWorker
from .exchange_info import exchange_info
from ..abstract import ABCExchange


class Binance(ABCExchange):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.symbol: str = self._signal.ticker

        self.binance: AsyncClient | None = None

    async def init_client(self) -> None:
        self.binance = await AsyncClient.create(
            api_key=self._secrets.binance_api_key,
            api_secret=self._secrets.binance_api_secret)
        print(await self.binance.get_account_api_permissions())

    async def process_signal(self) -> None:
        try:
            await self.init_client()

            # cant open new position if old exists
            position_info = await self.binance.futures_position_information(symbol=self.symbol)
            if float(position_info[0]["positionAmt"]) != 0:
                logger.info(f"Позиция по {self.symbol} уже открыта.")
                return

            # cancel all old orders to place new
            await self.binance.futures_cancel_all_open_orders(symbol=self.symbol)

            side: str = SIDE_BUY if self._signal.take_profit > self._signal.stop_loss else SIDE_SELL

            futures_ticker: dict = await self.binance.futures_symbol_ticker(symbol=self.symbol)
            last_price: float = float(futures_ticker["price"])

            quantity: float = self.calculate_position_quantity(
                risk_usdt=self._user_strategy.risk_usdt,
                last_price=last_price,
                side=side
            )

            market_order: dict = self.create_order_kwargs(
                type_=FUTURE_ORDER_TYPE_MARKET,
                quantity=quantity,
                side=side,
            )

            # open orders
            await self.create_batch_orders(orders=[market_order])

        except Exception as e:
            logger.exception(f"Error while process signal: {e}")
            await AlertWorker.send_alert(f"Ошибка при обработке сигнала: {e}")

    async def create_batch_orders(self, orders: list[dict]) -> None:
        result = await self.binance.futures_place_batch_order(batchOrders=json.dumps(orders))
        for r in result:
            if not isinstance(r, dict) or isinstance(r, dict) and "code" in r:
                raise Exception(f"{result}")
            await AlertWorker.send_alert(f"Открыт ордер: {r}")

    def calculate_position_quantity(self, risk_usdt: float, last_price: float, side: str) -> float:
        if side == SIDE_BUY:
            delta_percents: float = self._signal.stop_loss / last_price - 1
        elif side == SIDE_SELL:
            delta_percents: float = 1 - last_price / self._signal.stop_loss
        else:
            raise ValueError("Wrong position side")
        return risk_usdt / delta_percents

    @log_args
    def create_order_kwargs(self, type_: str, side: str,
                            quantity: Optional[float] = 0,
                            reduce_only: Optional[bool] = False,
                            close_position: Optional[bool] = False,
                            price: Optional[float] = 0,
                            stop_price: Optional[float] = 0,
                            time_in_force: Optional[str] = TIME_IN_FORCE_GTC,
                            callback_rate: Optional[float] = 0.0,
                            client_order_id: Optional[str] = None,
                            ) -> dict:
        kwargs = {
            'symbol': self.symbol,
            'type': type_,
            'side': side
        }

        if client_order_id:
            kwargs['newClientOrderId'] = client_order_id

        # Here will be one place where price and qty rounds
        quantity = abs(exchange_info.round_quantity(self.symbol, quantity))
        price = exchange_info.round_price(self.symbol, price)
        stop_price = exchange_info.round_price(self.symbol, stop_price)

        if type_ == FUTURE_ORDER_TYPE_MARKET:
            kwargs['quantity'] = str(quantity)

        elif type_ == FUTURE_ORDER_TYPE_LIMIT:
            kwargs['price'] = str(price)
            kwargs['reduceOnly'] = str(reduce_only)
            kwargs['timeInForce'] = str(time_in_force)
            kwargs['quantity'] = str(quantity)

        elif type_ == FUTURE_ORDER_TYPE_STOP:
            kwargs['quantity'] = str(quantity)
            kwargs['stopPrice'] = str(stop_price)
            kwargs['price'] = str(price)

        elif type_ == FUTURE_ORDER_TYPE_STOP_MARKET:
            kwargs['stopPrice'] = str(stop_price)
            kwargs['closePosition'] = str(close_position)
            kwargs['quantity'] = str(quantity)

        elif type_ == FUTURE_ORDER_TYPE_TAKE_PROFIT_MARKET:
            kwargs['stopPrice'] = str(stop_price)
            kwargs['closePosition'] = str(close_position)

        elif type_ == FUTURE_ORDER_TYPE_TRAILING_STOP_MARKET:
            kwargs['reduceOnly'] = str(reduce_only)
            kwargs['quantity'] = str(quantity)
            kwargs['activationPrice'] = str(price)
            kwargs['callbackRate'] = str(callback_rate)

        return kwargs
