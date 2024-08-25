"""
Module that rounds prices and quantities for symbols
"""
__all__ = ["exchange_info", ]

import re
import time

import requests

from app.config import logger
from ..abstract import ABCExchangeInfo


class ExchangeInfo(ABCExchangeInfo):
    precisions: dict[str, list[int]] = {}

    @classmethod
    def run(cls):
        """Update symbols decimals for OKX Perpetual Futures."""
        while True:
            try:
                url = "https://www.okx.com/api/v5/public/instruments?instType=SWAP"
                data = requests.get(url).json()["data"]
                for el in data:
                    tick_size = el["tickSz"]
                    # step_size = el["lotSz"]
                    step_size = el["ctVal"]

                    tick_size = list(re.sub('0+$', '', tick_size))
                    if len(tick_size) == 1:
                        tick_size = 1
                    else:
                        tick_size = len(tick_size) - 2

                    step_size = list(re.sub('0+$', '', step_size))
                    if len(step_size) == 1:
                        step_size = 0
                    else:
                        step_size = len(step_size) - 2

                    cls.precisions[el["instId"]] = [tick_size, step_size]

            except Exception as error:
                logger.error(f"{type(error)} in run method for OKX: {error}.")
            time.sleep(60 * 60)

    @classmethod
    def round_price(cls, symbol: str, price: float) -> float:
        """
        Round price
        :param symbol:
        :param price:
        :return:
        """
        try:
            return round(price, cls.precisions[symbol.upper()][0])
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
            return round(quantity, cls.precisions[symbol.upper()][1])
        except KeyError as e:
            logger.error(f"KeyError while rounding quantity {symbol}: {e}")
            return quantity


exchange_info = ExchangeInfo()
exchange_info.start()
