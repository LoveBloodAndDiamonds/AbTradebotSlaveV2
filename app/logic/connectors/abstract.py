from abc import ABC, abstractmethod
from threading import Thread

from ..schemas import Signal, UserStrategySettings


class ABCExchange(ABC):

    def __init__(
            self,
            signal: Signal,
            user_strategy: UserStrategySettings,
            api_key: str,
            api_secret: str
    ) -> None:
        self._api_key = api_key
        self._api_secret = api_secret
        self._signal = signal
        self._user_strategy = user_strategy

        self.symbol: str = self._signal.ticker
        self.side: str = NotImplemented
        self.last_price: float = NotImplemented
        self.quantity: float = NotImplemented

    @abstractmethod
    async def process_signal(self) -> bool:
        pass


class ABCExchangeInfo(ABC, Thread):
    """
    Класс, который внутри себя обновляет информацию о том, как надо округлять
    цены монет и их количество в ордерах на разных биржах.
    """

    def __init__(self):
        Thread.__init__(self, daemon=True)

    @abstractmethod
    def run(self) -> None:
        pass

    @abstractmethod
    def round_price(self, symbol: str, price: float) -> float:
        pass

    @abstractmethod
    def round_quantity(self, symbol: str, quiantity: float) -> float:
        pass
