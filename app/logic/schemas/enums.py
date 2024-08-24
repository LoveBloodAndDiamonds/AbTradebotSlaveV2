from enum import Enum


class Side(Enum):
    BUY = "BUY"
    SELL = "SELL"


class BreakevenType(Enum):
    PLUS = "PLUS"
    MINUS = "MINUS"
