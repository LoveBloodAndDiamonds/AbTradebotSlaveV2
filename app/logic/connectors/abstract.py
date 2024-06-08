from abc import ABC, abstractmethod
from threading import Thread

from ..schemas import Signal, UserStrategySettings
from ...database import SecretsORM, Database


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


class ABCPositionWarden(ABC):

    @abstractmethod
    async def start_warden(self) -> None:
        """
        Функция запускает бесконечный цикл, в котором проверяются открытые позиции без стопов.
        :return:
        """

    def _find_common_elements(
            self,
            prev_iteration: list[dict],
            curr_iteration: list[dict]
    ) -> list[dict]:
        """
        Функция находит одинаковые элементы в списках из текущей и прошлой итерации.
        Одинаковыми элментами являются позиции - которые нужно закрыть.
        :return:
        """
        common_elements: list[dict] = []
        for position in curr_iteration:
            if position in prev_iteration:
                common_elements.append(position)

        return common_elements

    # @abstractmethod
    # async def _close_positions(self, positions_to_close: list[dict]) -> None:
    #     """
    #     Функиця закрывает позиции и отменяет ордера.
    #     :param positions_to_close: [{symbol: BTCUSDT, positionAmt: 0.01}, ...]
    #     :return:
    #     """
    #
    # def _find_common_elements(
    #         self,
    #         prev_iteration: list[dict],
    #         curr_iteration: list[dict]
    # ) -> list[dict]:
    #     """
    #     Функция находит одинаковые элементы в списках из текущей и прошлой итерации.
    #     Одинаковыми элментами являются позиции - которые нужно закрыть.
    #     :return:
    #     """
    #     common_elements: list[dict] = []
    #     for position in curr_iteration:
    #         if position in prev_iteration:
    #             common_elements.append(position)
    #
    #     return common_elements
    #
    #
    # def _check_positions_health(self, positions: list[dict], orders: list[dict]) -> list[dict]:
    #     """
    #     Функция проверяет, чтобы на позиции обязательно стоял стоп-ордер.
    #     :param positions:
    #     :param orders:
    #     :return: [{symbol: BTCUSDT, positionAmt: 0.01}, ...]
    #     """

    # @abstractmethod
    # async def _get_open_orders(self) -> list[dict]:
    #     """
    #     Функция возвращает все открытые ордера на аккаунте.
    #     Если их нет - возвращает пустой список.
    #     """

    # @abstractmethod
    # async def _get_open_positions(self) -> list[dict]:
    #     """
    #     Функция возвращает все открытые позиции на аккаунте.
    #     Если их нет - возвращает пустой список.
    #     """
