from typing import TypedDict


class SignalDict(TypedDict):
    strategy: str
    ticker: str
    exchange: str
    take_profit: float
    stop_loss: float
    plus_breakeven: float
    minus_breakeven: float
