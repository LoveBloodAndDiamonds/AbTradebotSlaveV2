from dataclasses import dataclass

from .exchange import Exchange


@dataclass
class Signal:
    strategy: str
    ticker: str
    exchange: Exchange
    take_profit: float
    stop_loss: float
    breakeven: float

    def as_dict(self) -> dict:
        return {
            "strategy": self.strategy,
            "ticker": self.ticker,
            "exchange": self.exchange.value,
            "take_profit": self.take_profit,
            "stop_loss": self.stop_loss,
            "breakeven": self.breakeven
        }

    @classmethod
    def from_dict(cls, signal_dict: dict) -> "Signal":
        return cls(
            strategy=signal_dict["strategy"],
            ticker=signal_dict["ticker"],
            exchange=Exchange[signal_dict["exchange"]],
            take_profit=signal_dict["take_profit"],
            stop_loss=signal_dict["stop_loss"],
            breakeven=signal_dict["breakeven"]
        )

    def __str__(self) -> str:
        return str(self.as_dict())
