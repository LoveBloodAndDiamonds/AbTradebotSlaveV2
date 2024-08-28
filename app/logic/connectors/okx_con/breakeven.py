__all__ = ["OKXBreakevenWebSocket", ]

import asyncio
import json

import websockets
from websockets import WebSocketClientProtocol

from app.config import logger
from app.logic.schemas import BreakevenTask, Side, Candle, BreakevenType
from app.logic.utils import CandlesSorter, AlertWorker
from ..abstract import ABCBreakevenWebSocket


class OKXBreakevenWebSocket(ABCBreakevenWebSocket):
    """
    Класс существует для определения момента, когда нужно переставить безубыток.
    """
    # __KLINES_WS_URL: str = "wss://ws.okx.com:8443/ws/v5/public"
    __KLINES_WS_URL: str = "wss://ws.okx.com:8443/ws/v5/business"
    __PING_INTERVAL_SECONDS: int = 10

    def __init__(self, task: BreakevenTask, workers: int = 1) -> None:
        if not any([task.plus_breakeven, task.minus_breakeven]):
            logger.info(f"Breakeven prices on {task.ticker} okx was not defined!")
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
        if self.__in_progress:
            logger.info(f"Breakeven task started {self._task}")
            loop = asyncio.get_running_loop()
            loop.create_task(self._start_logic())  # noqa
        else:
            logger.info("Breakeven task no need to be launched")

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

                            try:
                                msg_dict: dict = json.loads(msg_str)
                            except json.decoder.JSONDecodeError as e:
                                if msg_str != "pong":
                                    raise e
                                continue

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
                logger.exception(f"Error while recv klines ws message from okx.com: {e}")
            await asyncio.sleep(1)

    async def _worker(self) -> None:
        """
        Обрабатываем сообщение из вебсокета.
        """

        while self.__in_progress:
            try:
                msg: dict = await self.__queue.get()
                # {'arg': {'channel': 'candle1M', 'instId': 'MATIC-USDT-SWAP'}, 'data': [
                # ['1722441600000', '0.5133', '0.582', '0.3336', '0.4985', '388253062', '3882530620', '1794321105.114',
                # '0']]}

                if "event" in msg:
                    continue

                kline = msg["data"][0]
                for v in self.__sorter.get_new_values(
                        candle=Candle(
                            open_time=float(kline[0]),
                            open=float(kline[1]),
                            high=float(kline[2]),
                            low=float(kline[3]),
                            close=float(kline[4]),
                            volume=float(kline[5]),
                            is_closed=bool(int(kline[-1]))
                        )
                ):
                    async def _at_find_breakeven(be_type: BreakevenType):
                        logger.info(f"Detected {be_type} on kline: {kline}")
                        self._stop()
                        await self.task().callback(be_type)

                    if self.__side == Side.BUY:
                        if v >= self._task.plus_breakeven:
                            return await _at_find_breakeven(BreakevenType.PLUS)
                        elif v <= self._task.minus_breakeven:
                            return await _at_find_breakeven(BreakevenType.MINUS)
                        elif not self._task.stop_loss <= v <= self._task.take_profit:
                            self._stop()
                            logger.error(f"Error on {self._task.__dict__}: "
                                         f"Breakven not detected but already take or stop!")

                    elif self.__side == Side.SELL:
                        if self._task.plus_breakeven >= v:
                            return await _at_find_breakeven(BreakevenType.PLUS)
                        elif self._task.minus_breakeven <= v:
                            return await _at_find_breakeven(BreakevenType.MINUS)
                        elif not self._task.stop_loss >= v >= self._task.take_profit:
                            self._stop()
                            logger.error(f"Error on {self._task.__dict__}: "
                                         f"Breakven not detected but already take or stop!")

                    else:
                        raise ValueError(f"Wrong side to task: {self._task.__dict__}: {self.__side}")
            except Exception as e:
                logger.exception(f"Error while handle kline from okx ws: {e}")

    async def _subscribe_klines(self) -> None:
        """
        Функция подписывается на топик с klines.
        :return:
        """
        msg = {
            "op": "subscribe",
            "args": [{"channel": "candle1M", "instId": self._task.ticker}]
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
                    # msg: str = "ping"
                    # await self.__ws.send(json.dumps(msg))
                    await self.__ws.send("ping")
                except Exception as e:
                    logger.error(f"Error while ping okx.com: {e}")
            await asyncio.sleep(self.__PING_INTERVAL_SECONDS)

    def _stop(self) -> None:
        logger.debug(f"Break okx.com klines ws for {self._task.ticker}")
        self.__in_progress: bool = False
