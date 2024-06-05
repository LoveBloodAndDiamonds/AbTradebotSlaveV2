import asyncio
import json
from datetime import datetime

import aiohttp
import websockets

from app.config import logger, VERSION, WS_RECONNECT_TIMEOUT, WS_WORKERS_COUNT
from app.database import Database, SecretsORM
from .exchanges import EXCHANGES
from .schemas import UserStrategySettings, Signal
from .utils import AlertWorker


class Logic:
    """
    Класс представляет возможность получать данные с главного сервера, а так же
    прослушивать сообщения с сигналами и запускать эти сигналы.
    """

    def __init__(self, secrets: SecretsORM, db: Database) -> None:
        # Обьект базы данных для обновления секретных данных
        self._db = db
        self._secrets = secrets

        # Ключ лицензии, хост и порт для составления url запросов
        self._license_key: str = secrets.license_key
        _, self._host, self._port = self._parse_license_key()

        # Очередь сообщений с вебсокета.
        self._queue: asyncio.Queue = asyncio.Queue()

        # Словарь с активными стратегиями юзера
        self._active_strategies: dict[str, UserStrategySettings] = {}

        # Инициализируем класс, который отвечает за отправление алертов пользователю
        AlertWorker.init(secrets=self._secrets)

    async def start_logic(self) -> None:
        """
        Запуск логики соединения с мастер-вебсокетом.
        :return:
        """
        # await self._queue.put(
        #     {
        #         "strategy": "test",
        #         "ticker": "XRPUSDT",
        #         "exchange": "BINANCE",
        #         "take_profit": 0.54,
        #         "stop_loss": 0.52,
        #         "breakeven": 0.54
        #     }
        # )
        # self._active_strategies["test"] = UserStrategySettings(
        #     risk_usdt=1,
        #     trades_count=None
        # )

        # Создаем задачи для рабочих
        workers = [asyncio.create_task(self._worker()) for _ in range(WS_WORKERS_COUNT)]

        # Запускаем асихнронный сбор и обработку информации
        await asyncio.gather(self._connect_to_master(), *workers)

    def _parse_license_key(self) -> list[str]:
        """
        Получение хоста и порта, которые содержатся в ключе лицензии.
        :return:
        """
        return self._license_key.split(":")

    async def _update_secrets(self) -> None:
        """
        Функция обновляет секретные данные.
        Это нужно например перед тем, как открыть позицию, чтобы иметь актуальные
        API ключи с бирж.
        :return:
        """
        self._secrets: SecretsORM = await self._db.secrets_repo.get()

    async def _connect_to_master(self) -> None:
        """
        Получаем сообщения с вебсокета с главного сервера.
        :return:
        """
        while True:
            try:
                url: str = f"ws://{self._host}:{self._port}/ws/{VERSION}/{self._license_key}"
                async with (websockets.connect(url) as ws):  # ws: WebSocketClientProtocol
                    try:
                        logger.success(f"WS connected to: {url}")
                        while True:
                            msg_str: str = await ws.recv()
                            msg_dict: dict = json.loads(msg_str)
                            await self._queue.put(msg_dict)
                    except Exception as e:
                        if isinstance(e, websockets.exceptions.ConnectionClosed):
                            logger.error(f"WS Connection error in recv ws msg: {e}")
                        else:
                            logger.exception(f"WS Unknown error in recv ws msg: {e}")
                        logger.info(f"Reconnect to WS in {WS_RECONNECT_TIMEOUT} seconds")
                        await asyncio.sleep(WS_RECONNECT_TIMEOUT)
                        await ws.close()
                        continue
            except Exception as e:
                _: str = f"WS Fatal ws error: {e}"
                logger.critical(_)
                logger.exception(_)
                await asyncio.sleep(1)

    async def _worker(self) -> None:
        """
        Рабочий, который обрабатывает сообщения из очереди, которые в свою очередь получены
        с мастер вебсокета.
        Таких рабочих может быть несколько, чтобы успевать обрабатывать сразу несколько сигналов.
        :return:
        """
        # todo
        while True:
            try:
                msg: dict = await self._queue.get()
                signal: Signal = Signal.from_dict(signal_dict=msg)
                if signal.strategy in self._active_strategies:
                    user_strategy: UserStrategySettings = self._active_strategies[signal.strategy]
                    logger.info(f"Got {signal} from ws")
                    await AlertWorker.send_alert(f"Получен сигнал по стратегии {signal.strategy}")
                    secrets: SecretsORM = await self._db.secrets_repo.get()
                    exchange = EXCHANGES[signal.exchange](
                        secrets=secrets,
                        signal=signal,
                        user_strategy=user_strategy
                    )
                    await exchange.process_signal()

                    if user_strategy.trades_count is not None:
                        self._active_strategies[signal.strategy].trades_count -= 1
                        if self._active_strategies[signal.strategy].trades_count == 0:
                            await AlertWorker.send_alert(f"Стратегия {signal.strategy} "
                                                         f"выполнила указанное количество сделок.")
                            del self._active_strategies[signal.strategy]
                            return

                else:
                    logger.debug(f"Ignore {signal} from ws")

            except json.decoder.JSONDecodeError:
                logger.error(f"WS Error while decode msg: {msg}")
            except Exception as e:
                logger.exception(f"WS Error in _worker func: {msg} : {e}")
            finally:
                self._queue.task_done()

    async def get_license_key_expired_date(self) -> datetime:
        """
        Функция получает время истечения подписки в формате timestamp и возвращает
        его в формате datetime.
        :return:
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://{self._host}:{self._port}/license_key/{self._license_key}") as responce:
                result: dict = await responce.json()
                if result["error"]:
                    raise Exception(result["error"])
                return datetime.fromtimestamp(result["result"])

    async def add_user_strategy(self, strategy_name: str, risk_usdt: float, trades_count: int | None) -> None:
        """
        Функция добавляет стратегию в словарь активных стратегий.
        :param strategy_name: Название стратегии
        :param risk_usdt: Риск в долларах
        :param trades_count: Количество сделок, если None - то бесконечность.
        :return: None
        """
        # Проверка на то, запущена ли уже стратегния.
        if strategy_name.lower() in self._active_strategies:
            raise ValueError(f"Стратегия {strategy_name} уже запущена.")

        # Првоерка - существует ли такая стратегия на сервере.
        server_strategis: list[str] = await self._get_server_available_strategies()
        if strategy_name.lower() not in server_strategis:
            raise ValueError(f"Стратегии {strategy_name} нет в списке стратегий.\n"
                             f"Доступные стратегии: {server_strategis}")

        # Добавление обьекта стратегии в словарь активных стратегий
        self._active_strategies[strategy_name.lower()] = UserStrategySettings(
            risk_usdt=risk_usdt,
            trades_count=trades_count)

    def remove_user_startegy(self, strategy_name: str = "", stop_all: bool = False) -> None:
        """
        Функция удаляет активную стратегию пользователя.
        :param strategy_name: Название стратегии
        :param stop_all: Остановить все?
        :return:
        """
        if stop_all:  # Остановка всех стратегий
            self._active_strategies: dict[str, UserStrategySettings] = {}
        else:  # Остановка одной стратегии
            if strategy_name.lower() not in self._active_strategies:  # Проверка на существование стратегии
                raise ValueError(f"Стратегия {strategy_name} не существует или не запущена.")
            del self._active_strategies[strategy_name.lower()]

    async def _get_server_available_strategies(self) -> list[str]:
        """
        Функция получает список активных стратегий с главного сервера.
        :return:
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://{self._host}:{self._port}/strategies/{self._license_key}") as responce:
                result: dict = await responce.json()
                if result["error"]:
                    raise Exception(result["error"])
                return result["result"]

    def get_active_user_strategies(self) -> dict[str, UserStrategySettings]:
        """
        Функция возвращает словарь с активными стратегиями пользователя.
        :return:
        """
        return self._active_strategies
