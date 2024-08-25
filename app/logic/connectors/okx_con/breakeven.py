__all__ = ["OKXBreakevenWebSocket", ]

import asyncio

from websockets import WebSocketClientProtocol

from app.config import logger
from app.logic.schemas import BreakevenTask, Side
from app.logic.utils import CandlesSorter
from ..abstract import ABCBreakevenWebSocket


class OKXBreakevenWebSocket(ABCBreakevenWebSocket):
    """
    Класс существует для определения момента, когда нужно переставить безубыток.
    """

    def __init__(self, task: BreakevenTask, workers: int = 1) -> None:
        if not any([task.plus_breakeven, task.minus_breakeven]):
            logger.info(f"Breakeven prices on {task.ticker} bybit was not defined!")
            return

        super().__init__(task=task)

        self.__workers: int = workers
        self.__queue: asyncio.Queue = asyncio.Queue()

        self.__sorter: CandlesSorter = CandlesSorter()
        self.__side: Side | NotImplemented = self._define_side_by_task()

        self.__ws: WebSocketClientProtocol | None = None
        self.__in_progress: bool = True

    def task(self) -> BreakevenTask:
        return self._task

    async def run(self) -> None:
        """ Функция запускает все процессы, которые нужны для отслеживания безубытка. """
        logger.info(f"Breakeven task started {self._task}")
        loop = asyncio.get_running_loop()
        loop.create_task(self._start_logic())  # noqa
