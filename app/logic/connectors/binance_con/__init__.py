__all__ = ["Binance", ]

from .binance_exc import Binance


def _define_position_quantity(self) -> None:
    """
    Функция определяет размер позиции.
    :return:
    """
    # unrounded_qty = risk / (percent_to_stop * orders.first_limit)

    if self.side == SIDE_BUY:
        # "calculation": lambda: (strategy.long_orders.first_limit / strategy.long_orders.stop - 1),
        percents_to_stop: float = self.last_price / self._signal.stop_loss - 1
    elif self.side == SIDE_SELL:
        # "calculation": lambda: (1 - strategy.short_orders.first_limit / strategy.short_orders.stop),
        percents_to_stop: float = 1 - self.last_price / self._signal.stop_loss
    else:
        raise ValueError("Wrong position side")
    logger.warning(percents_to_stop)
    self.quantity = self._user_strategy.risk_usdt / (percents_to_stop * self.last_price)
    # self.quantity = self._user_strategy.risk_usdt / delta_percents