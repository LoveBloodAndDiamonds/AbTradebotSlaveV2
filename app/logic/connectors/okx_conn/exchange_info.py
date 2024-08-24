"""
Module that rounds prices and quantities for symbols
"""
__all__ = ["exchange_info", ]

import re
import time

from binance import Client

from app.config import logger
from ..abstract import ABCExchangeInfo


class ExchangeInfo(ABCExchangeInfo):
    precisions: dict[str: list[int, int]] = {}

    @classmethod
    def run(cls) -> None:
        pass  # todo

    @classmethod
    def round_price(cls, symbol: str, price: float) -> float:
        """
        Round price
        :param symbol:
        :param price:
        :return:
        """
        try:
            return round(price, cls.precisions[symbol.upper()]["price"])
        except KeyError as e:
            logger.error(f"KeyError while rounding price {symbol}: {e}")

    @classmethod
    def round_quantity(cls, symbol: str, quantity: float) -> float:
        """
        Round quantity
        :param symbol:
        :param quantity:
        :return:
        """
        try:
            return round(quantity, cls.precisions[symbol.upper()]["quantity"])
        except KeyError as e:
            logger.error(f"KeyError while rounding quantity {symbol}: {e}")
            return quantity


exchange_info = ExchangeInfo()
exchange_info.start()
