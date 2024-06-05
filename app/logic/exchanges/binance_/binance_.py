from typing import Optional

from binance.enums import *

from app.config import log_args
from .exchange_info import exchange_info
from ..abstract import Exchange


class Binance(Exchange):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.symbol: str = self._signal.ticker

    async def handle_signal(self) -> None:
        # Получить текущую цену
        # Посчитать размер позиции
        # Открыть маркет ордер (или попробовать открыть сразу три ордера)
        # Открыть три ордера
        pass

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
