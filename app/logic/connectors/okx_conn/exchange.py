from ..abstract import ABCExchange
from ...schemas import BreakevenType


class OKX(ABCExchange):

    async def process_signal(self) -> bool:
        """ Функция обрабатывает полученный сигнал. """
        pass

    async def _handle_breakeven_event(self, be_type: BreakevenType):
        """ Функция принимает каллбек для события, когда нужно переставить безубыток. """
        pass
