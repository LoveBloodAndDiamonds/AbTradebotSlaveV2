from enum import Enum

from ..schemas import Candle


class CandleColor(Enum):
    RED = "RED"
    GREEN = "GREEN"
    NOT_DEFINED = "NOT_DEFINED"


class CandlesSorter:
    """
    This class filter new values in each kline and return it.
    """

    """
    Hint:
    if candle red: OHLC = c.c < c.o
    if candle green: OLHC = c.c > c.o
    
    If color NOT_DEFINED and candle is new: return only close
    """

    def __init__(self):
        self.prev_candle: Candle | None = None

    def get_new_values(self, candle: Candle) -> list[float]:
        """
        Chose new values and return it
        :param candle:
        :return:
        """
        color = self._define_color(candle)

        # Первая загруженная свеча
        if self.prev_candle is None:
            self.prev_candle = candle
            return self._condition_values(color=color, _close=candle.close)

        # Новая свеча
        if self.prev_candle.open_time != candle.open_time:
            self.prev_candle = candle
            return self._condition_values(
                color, _open=candle.open, _close=candle.close, _high=candle.high, _low=candle.low)

        new_values = self._collect_new_values(candle)
        self.prev_candle = candle
        return self._condition_values(color, **new_values)

    def _collect_new_values(self, candle: Candle) -> dict[str, float]:
        """
        Collect new values
        :return:
        """
        oclh = dict()
        if candle.open != self.prev_candle.open:
            oclh["_open"] = candle.open
        if candle.close != self.prev_candle.close:
            oclh["_close"] = candle.close
        if candle.high != self.prev_candle.high:
            oclh["_high"] = candle.high
        if candle.low != self.prev_candle.low:
            oclh["_low"] = candle.low

        return oclh

    @staticmethod
    def _define_color(candle: Candle) -> CandleColor:
        """
        Define candle color
        :param candle:
        :return:
        """
        if candle.close < candle.open:
            return CandleColor.RED
        elif candle.close > candle.open:
            return CandleColor.GREEN
        else:
            return CandleColor.NOT_DEFINED

    @staticmethod
    def _condition_values(
            color: CandleColor,
            _open: float = False,
            _close: float = False,
            _high: float = False,
            _low: float = False
    ) -> list[float]:
        """
        Return values in need consistency on candle color.
        :param color:
        :param _open:
        :param _close:
        :param _high:
        :param _low:
        :return:
        """
        consistency = [_open, _low, _high, _close] if color == CandleColor.GREEN else \
            [_open, _high, _low, _close]

        return [value for value in consistency if value]

        # non_false_values = [value for value in consistency if value]
        # unique_values = list(set(non_false_values))
