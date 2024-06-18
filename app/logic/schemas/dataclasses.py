from dataclasses import dataclass
from typing import Callable, Awaitable

from .enums import Exchange


@dataclass
class Signal:
    strategy: str
    ticker: str
    exchange: Exchange
    take_profit: float
    stop_loss: float
    plus_breakeven: float
    minus_breakeven: float

    def as_dict(self) -> dict:
        as_dict: dict = self.__dict__
        as_dict["exchange"] = self.exchange.value

        return as_dict

    @classmethod
    def from_dict(cls, signal_dict: dict) -> "Signal":
        return cls(
            strategy=signal_dict["strategy"].lower(),
            ticker=signal_dict["ticker"],
            exchange=Exchange[signal_dict["exchange"]],
            take_profit=signal_dict["take_profit"],
            stop_loss=signal_dict["stop_loss"],
            minus_breakeven=signal_dict["minus_breakeven"],
            plus_breakeven=signal_dict["plus_breakeven"]
        )


@dataclass
class UserStrategySettings:
    risk_usdt: float
    trades_count: int | None


@dataclass
class Candle:
    open_time: float
    open: float
    high: float
    low: float
    close: float
    volume: float
    is_closed: bool


@dataclass
class BreakevenTask:
    ticker: str
    take_profit: float
    stop_loss: float
    plus_breakeven: float
    minus_breakeven: float
    callback: Callable[..., Awaitable]

    meta: str = ""

    def __str__(self) -> str:
        return f"BreakevenTask({self.__dict__})"

    @property
    def as_log(self) -> str:
        return f"+{self.plus_breakeven}, -{self.minus_breakeven}"
