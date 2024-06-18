__all__ = ["BybitBreakevenWebSocket", ]

import asyncio
import json
import time

import websockets
from websockets import WebSocketClientProtocol

from app.config import logger
from app.logic.schemas import BreakevenTask, Side, Candle, BreakevenType
from app.logic.utils import CandlesSorter, AlertWorker
from ..abstract import ABCBreakevenWebSocket


class BybitBreakevenWebSocket(ABCBreakevenWebSocket):
    """
    Класс существует для определения момента, когда нужно переставить безубыток.
    """
    __KLINES_WS_URL: str = "wss://stream.bybit.com/v5/public/linear"
    __PING_INTERVAL_SECONDS: int = 10

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

    async def _start_logic(self) -> None:
        # Логируем запуск
        await AlertWorker.info(f"Цены активации безубытка: {self._task.as_log}")

        # Запускаем обработку сообщений с вебсокета несколькими рабочими
        workers = [asyncio.create_task(self._worker()) for _ in range(self.__workers)]

        # Запускаем асихнронный сбор и обработку информации
        await asyncio.gather(self._recv_ws_msg(), *workers, self._ping_task())

    async def _recv_ws_msg(self) -> None:
        """
        Получаем сообщения из вебсокета.
        :return:
        """
        while self.__in_progress:
            try:
                async with websockets.connect(self.__KLINES_WS_URL) as ws:  # ws: WebSocketClientProtocol
                    self.__ws = ws
                    try:
                        logger.debug(f"WS connected to {self.__KLINES_WS_URL}")
                        await self._subscribe_klines()
                        while self.__in_progress:
                            msg_str: str = await ws.recv()
                            msg_dict: dict = json.loads(msg_str)
                            await self.__queue.put(msg_dict)
                            await asyncio.sleep(.001)
                    except (websockets.exceptions.ConnectionClosedError,
                            websockets.exceptions.ConnectionClosedOK,
                            websockets.exceptions.ConnectionClosed) as e:
                        logger.error(f"WS Connection error in recv ws msg: {e}")
                        await ws.close()
                        continue
                    except Exception as e:
                        logger.exception(f"WS Unknown error in recv ws msg: {e}")
                        await ws.close()
                        continue
            except Exception as e:
                logger.exception(f"Error while recv klines ws message from bybit.com: {e}")
            await asyncio.sleep(1)

    async def _worker(self) -> None:
        """
        Обрабатываем сообщение из вебсокета.
        {'topic': 'kline.1.TRXUSDT', 'data': [
        {'start': 1718698440000, 'end': 1718698499999, 'interval': '1', 'open': '0.11506', 'close': '0.11506',
         'high': '0.11507', 'low': '0.11506', 'volume': '4925', 'turnover': '566.67476', 'confirm': False,
         'timestamp': 1718698456278}], 'ts': 1718698456278, 'type': 'snapshot'}
        """

        while self.__in_progress:
            msg: dict = await self.__queue.get()
            if not msg.get("topic"):
                continue

            kline: dict = msg["data"][0]
            for v in self.__sorter.get_new_values(
                    candle=Candle(
                        open_time=kline["start"],
                        is_closed=kline["confirm"],
                        high=float(kline["high"]),
                        low=float(kline["low"]),
                        close=float(kline["close"]),
                        open=float(kline["open"]),
                        volume=float(kline["volume"])
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

    async def _subscribe_klines(self) -> None:
        """
        Функция подписывается на топик с klines.
        :return:
        """
        # kline.{interval}.{symbol}
        msg = {
            "req_id": f"{time.time()}",
            "op": "subscribe",
            "args": [
                f"kline.1.{self._task.ticker}"
            ]
        }
        await self.__ws.send(json.dumps(msg))

    async def _ping_task(self):
        """
        Функция в цикле отправляет ping на биржу, чтобы она нас не отключала от вебсокета.
        :return:
        """
        while self.__in_progress:
            if self.__ws is not None:
                try:
                    msg = {"req_id": "100001", "op": "ping"}
                    await self.__ws.send(json.dumps(msg))
                except Exception as e:
                    logger.error(f"Error while ping bybit.com: {e}")
            await asyncio.sleep(self.__PING_INTERVAL_SECONDS)

    def _stop(self) -> None:
        logger.debug(f"Break bybit.com klines ws for {self._task.ticker}")
        self.__in_progress: bool = False
