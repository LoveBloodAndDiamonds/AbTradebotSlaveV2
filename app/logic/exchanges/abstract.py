from abc import ABC, abstractmethod

from app.logic.schemas import Signal, UserStrategySettings


class Exchange(ABC):

    def __init__(self, signal: Signal, user_strategy: UserStrategySettings) -> None:
        self._signal = signal
        self._user_strategy = user_strategy

    @abstractmethod
    async def handle_signal(self) -> None:
        pass
