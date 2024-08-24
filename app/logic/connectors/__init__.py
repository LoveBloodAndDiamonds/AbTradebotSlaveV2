__all__ = ["EXCHANGES_CLASSES_FROM_ENUM", "BinanceWarden", "BybitWarden", "OKXWarden"]

from app.database import Exchange
from .abstract import ABCExchange
from .binance_con import Binance, BinanceWarden
from .bybit_con import Bybit, BybitWarden
from .okx_conn import OKX, OKXWarden

EXCHANGES_CLASSES_FROM_ENUM: dict[Exchange, type[ABCExchange]] = {
    Exchange.BINANCE: Binance,
    Exchange.BYBIT: Bybit,
    Exchange.OKX: OKX,
}
