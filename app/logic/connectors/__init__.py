__all__ = ["EXCHANGES_CLASSES_FROM_ENUM"]

from .abstract import ABCExchange
from .binance_con import Binance
from .bybit_con import Bybit
from ..schemas import Exchange

EXCHANGES_CLASSES_FROM_ENUM: dict[Exchange, type[ABCExchange]] = {
    Exchange.BINANCE: Binance,
    Exchange.BYBIT: Bybit
}
