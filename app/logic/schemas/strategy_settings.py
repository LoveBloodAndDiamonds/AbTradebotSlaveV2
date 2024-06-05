from dataclasses import dataclass


@dataclass
class UserStrategySettings:
    risk_usdt: float
    trades_count: int | None
