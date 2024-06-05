"""
Module that rounds prices and quantities for symbols
"""
__all__ = ["exchange_info", ]

import re
import time
from threading import Thread

from binance import Client

from app.config import logger


class ExchangeInfo(Thread):
    """
    Класс, который внутри себя обновляет информацию о том, как надо округлять
    цены монет и их количество в ордерах с binance.com.
    """

    binance = Client()
    precisions: dict[str: list[int, int]] = {}

    def __init__(self):
        super().__init__(daemon=True)

    def run(self):
        while True:
            try:
                exchange_info_dict: dict = self.binance.futures_exchange_info()
                for i in exchange_info_dict['symbols']:
                    filters = i['filters']
                    tick_size, step_size = None, None
                    for f in filters:
                        if f['filterType'] == 'PRICE_FILTER':
                            tick_size = f['tickSize']
                            tick_size = list(re.sub('0+$', '', tick_size))
                            if len(tick_size) == 1:
                                tick_size = 1
                            else:
                                tick_size = len(tick_size) - 2
                        if f['filterType'] == 'MARKET_LOT_SIZE':
                            step_size = f['stepSize']
                            step_size = list(re.sub('0+$', '', step_size))
                            if len(step_size) == 1:
                                step_size = 0
                            else:
                                step_size = len(step_size) - 2
                        self.precisions[i['symbol'].upper()] = {
                            "price": tick_size,
                            "quantity": step_size
                        }
            except Exception as e:
                logger.error(f"Preisions error: {e}")
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

    @classmethod
    def available_tickers(cls) -> list[str]:
        """
        Return list of available tickers in futures binance.com
        :return:
        """
        return list(cls.precisions.keys())


exchange_info = ExchangeInfo()
exchange_info.start()
