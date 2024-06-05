from .abstract import ABCExchange
from .binance_ import Binance

from ..schemas import Exchange


EXCHANGES: dict[Exchange, type[ABCExchange]] = {
    Exchange.BINANCE: Binance
}
