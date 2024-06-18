from enum import Enum


class Exchange(Enum):
    BINANCE = "BINANCE"
    BYBIT = "BYBIT"
    CAPITAL = "CAPITAL"


class Side(Enum):
    BUY = "BUY"
    SELL = "SELL"


class BreakevenType(Enum):
    PLUS = "PLUS"
    MINUS = "MINUS"
