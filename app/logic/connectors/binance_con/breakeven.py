__all__ = ["BinanceBreakevenWebSocket", ]

import asyncio

from binance import AsyncClient, BinanceSocketManager
from binance.streams import ReconnectingWebsocket

from app.config import logger
from app.logic.schemas import BreakevenTask, Candle, BreakevenType, Side
from app.logic.utils import CandlesSorter, AlertWorker
from ..abstract import ABCBreakevenWebSocket


class BinanceBreakevenWebSocket(ABCBreakevenWebSocket):

    def __init__(self, task: BreakevenTask, workers: int = 1) -> None:
        if not any([task.plus_breakeven, task.minus_breakeven]):
            logger.info(f"Breakeven prices on {task.ticker} binance was not defined!")
            self.inited: bool = False
            return
        else:
            self.inited: bool = True

        super().__init__(task=task)

        self.__workers: int = workers
        self.__queue: asyncio.Queue = asyncio.Queue()

        self.__sorter: CandlesSorter = CandlesSorter()
        self.__side: Side | NotImplemented = self._define_side_by_task()

        self.__in_progress: bool = True

    async def run(self) -> None:
        if self.inited:
            logger.info(f"Breakeven task started {self._task}")
            loop = asyncio.get_running_loop()
            loop.create_task(self._start_logic())  # noqa
        else:
            logger.info("Breakeven task no need to be launched")

    def _stop(self) -> None:
        logger.debug(f"Break binance.com klines ws for {self._task.ticker}")
        self.__in_progress: bool = False

    async def _start_logic(self) -> None:
        # Логируем запуск потока
        await AlertWorker.info(f"Цены активации безубытка: {self._task.as_log}")

        # Запускаем обработку сообщений с вебсокета несколькими рабочими
        workers = [asyncio.create_task(self._worker()) for _ in range(self.__workers)]

        # Запускаем асихнронный сбор и обработку информации
        await asyncio.gather(self._recv_ws_msg(), *workers)

    async def _recv_ws_msg(self) -> None:
        """
        Получаем сообщения из вебсокета.
        :return:
        """
        while self.__in_progress:
            try:
                async_client: AsyncClient = await AsyncClient.create()
                bsm: BinanceSocketManager = BinanceSocketManager(client=async_client)
                socket: ReconnectingWebsocket = bsm.kline_futures_socket(
                    symbol=self._task.ticker,
                    interval=async_client.KLINE_INTERVAL_1MINUTE)  # interval does not matter
                logger.info(f"Connecting to klines ws: {self._task.ticker}")
                async with socket as connection:
                    while self.__in_progress:
                        msg = await connection.recv()
                        await self.__queue.put(msg)
                        await asyncio.sleep(.01)
            except Exception as e:
                logger.exception(f"Error while recv klines ws message from binance.com: {e}")
            finally:
                await async_client.close_connection()
            await asyncio.sleep(1)

    async def _worker(self) -> None:
        """
        Обрабатываем сообщение из вебсокета.

        {'e': 'continuous_kline', 'E': 1718635208239, 'ps': 'XRPUSDT', 'ct': 'PERPETUAL',
         'k': {'t': 1718635200000, 'T': 1718635259999, 'i': '1m', 'f': 4803495293757, 'L': 4803496334736,
               'o': '0.5143', 'c': '0.5141', 'h': '0.5143', 'l': '0.5138', 'v': '671726.7', 'n': 746,
               'x': False, 'q': '345282.23757', 'V': '153110.7', 'Q': '78713.51763', 'B': '0'}}

        :return:
        """
        while self.__in_progress:
            msg: dict = await self.__queue.get()
            kline: dict = msg["k"]
            for v in self.__sorter.get_new_values(
                    candle=Candle(
                        open_time=kline["t"],
                        is_closed=kline["x"],
                        high=float(kline["h"]),
                        low=float(kline["l"]),
                        close=float(kline["c"]),
                        open=float(kline["o"]),
                        volume=float(kline["v"])
                    )
            ):

                async def _at_find_breakeven(be_type: BreakevenType):
                    logger.info(f"Detected {be_type} on kline: {kline}")
                    self._stop()
                    await self._task.callback(be_type)

                if self.__side == Side.BUY:
                    if v >= self._task.plus_breakeven:
                        return await _at_find_breakeven(BreakevenType.PLUS)
                    elif v <= self._task.minus_breakeven:
                        return await _at_find_breakeven(BreakevenType.MINUS)
                    elif not self._task.stop_loss <= v <= self._task.take_profit:
                        self._stop()
                        logger.error(f"Error on {self._task.__dict__}: Breakven not detected but already take or stop!")

                elif self.__side == Side.SELL:
                    if self._task.plus_breakeven >= v:
                        return await _at_find_breakeven(BreakevenType.PLUS)
                    elif self._task.minus_breakeven <= v:
                        return await _at_find_breakeven(BreakevenType.MINUS)
                    elif not self._task.stop_loss >= v >= self._task.take_profit:
                        self._stop()
                        logger.error(f"Error on {self._task.__dict__}: Breakven not detected but already take or stop!")

                else:
                    raise ValueError(f"Wrong side to task: {self._task.__dict__}: {self.__side}")
