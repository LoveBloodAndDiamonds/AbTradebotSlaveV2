from abc import ABC, abstractmethod

from app.database import SecretsORM
from app.logic.schemas import Signal, UserStrategySettings


class ABCExchange(ABC):

    def __init__(
            self,
            signal: Signal,
            user_strategy: UserStrategySettings,
            secrets: SecretsORM
    ) -> None:
        self._secrets = secrets
        self._signal = signal
        self._user_strategy = user_strategy

    @abstractmethod
    async def process_signal(self) -> None:
        pass
