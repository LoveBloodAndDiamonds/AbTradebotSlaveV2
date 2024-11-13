import asyncio
import json
from datetime import datetime

import aiohttp
import websockets

from app.config import logger, log_args, VERSION, WS_RECONNECT_TIMEOUT, WS_WORKERS_COUNT
from app.database import Database, SecretsORM, Exchange
from .connectors import EXCHANGES_CLASSES_FROM_ENUM, BinanceWarden, BybitWarden, ABCExchange, OKXWarden
from .schemas import UserStrategySettings, Signal, SignalDict
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
        # from app.logic.connectors.okx_con.breakeven import BreakevenTask, OKXBreakevenWebSocket
        # await OKXBreakevenWebSocket(BreakevenTask(
        #     ticker="MATIC-USDT-SWAP",
        #     take_profit=0.52,
        #     stop_loss=0.48,
        #     plus_breakeven=0.51,
        #     minus_breakeven=0.49,
        #     callback=None,
        #     meta="test",
        # )).run()
        # while True:
        #     await asyncio.sleep(10000)

        # await asyncio.sleep(4)
        # signal = Signal(
        #     strategy="zxcghoul",
        #     ticker="XRPUSDT",
        #     exchange=Exchange.BINANCE,
        #     take_profit=0.61,
        #     stop_loss=0.59,
        #     plus_breakeven=0,
        #     minus_breakeven=0,
        # )
        #
        # user_strategy = UserStrategySettings(
        #     risk_usdt=0.5,
        #     trades_count=1
        # )
        #
        # api_key, api_secret, passkey, exchange = await self._get_keys_and_exchange()
        # exchange = EXCHANGES_CLASSES_FROM_ENUM[exchange](
        #     api_key=api_key,
        #     api_secret=api_secret,
        #     api_pass=passkey,
        #     signal=signal,
        #     user_strategy=user_strategy)

        # from app.logic.schemas import BreakevenType
        # await exchange._init_client()
        # await exchange._handle_breakeven_event(BreakevenType.PLUS)

        # is_success: bool = await exchange.process_signal()
        #
        # logger.success(is_success)
        #
        # while True:
        #     await asyncio.sleep(10000)

        # Создаем задачи для рабочих
        workers = [asyncio.create_task(self._worker()) for _ in range(WS_WORKERS_COUNT)]

        # Создаем задачи для проверки стопов на позициях
        wardens = [
            asyncio.create_task(BinanceWarden(db=self._db).start_warden()),
            asyncio.create_task(BybitWarden(db=self._db).start_warden()),
            asyncio.create_task(OKXWarden(db=self._db).start_warden())
        ]

        # Запускаем все что нам нужно для работы программы:
        # - рабочие
        # - вебсокет соединение с мастер сервером
        # - проверка наличия стопов на позициях
        await asyncio.gather(
            self._connect_to_master(),
            *wardens,
            *workers
        )

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
            raise ValueError(f"Стратегии {strategy_name} нет в списке стратегий")

        # Добавление обьекта стратегии в словарь активных стратегий
        self._active_strategies[strategy_name.lower()] = UserStrategySettings(
            risk_usdt=risk_usdt,
            trades_count=trades_count)

        logger.info(f"Added <'{strategy_name}' {risk_usdt}$ {trades_count}> strategy")

    @log_args
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

    @log_args
    def get_active_user_strategies(self) -> dict[str, UserStrategySettings]:
        """
        Функция возвращает словарь с активными стратегиями пользователя.
        :return:
        """
        return self._active_strategies

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
                            logger.info(f"Got message: {msg_str}")
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
        while True:
            try:
                # Обновляем данные из базы данных
                await self._update_secrets()

                # Обрабатываем и валидируем сигнал
                msg: dict = await self._queue.get()
                signal: Signal = Signal.from_dict(signal_dict=msg)

                # Отсылаем алерт, если нужно
                if self._secrets.alerts:
                    await self._send_alert(source=msg)
                else:
                    logger.info("Alerts is turned off.")

                # Проыеряем есть ли стратегия в активных стратегияъ
                if signal.strategy not in self._active_strategies:
                    logger.debug(f"Ignore signal: {signal}")
                    continue
                else:
                    logger.info(f"Process signal: {signal}")

                # Запускаем стратегию
                api_key, api_secret, api_pass, exchange = await self._get_keys_and_exchange()
                exchange_obj: ABCExchange = EXCHANGES_CLASSES_FROM_ENUM[exchange](
                    api_key=api_key,
                    api_secret=api_secret,
                    api_pass=api_pass,
                    signal=signal,
                    user_strategy=self._active_strategies[signal.strategy])
                is_success: bool = await exchange_obj.process_signal()

                # Проверяем количество оставшихся сигналов, если сигнал успешно обработан
                if not is_success or self._active_strategies[signal.strategy].trades_count is None:
                    continue

                # Убалвяем количество оставшихся сделок и информируем юзера
                self._active_strategies[signal.strategy].trades_count -= 1
                await AlertWorker.info(
                    f"Осталось {self._active_strategies[signal.strategy].trades_count} сделок по {signal.strategy}.")

                # Удаляем стратегию из активных, если в ней не осталось сделок
                if self._active_strategies[signal.strategy].trades_count <= 0:
                    del self._active_strategies[signal.strategy]

            except json.decoder.JSONDecodeError:
                logger.error(f"WS Error while decode msg: {msg}")
            except Exception as e:
                _: str = f"WS Error in _worker func: {msg} : {e}"
                logger.exception(_)
                await AlertWorker.error(_)
            finally:
                self._queue.task_done()

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

    async def _get_keys_and_exchange(self) -> tuple[str, str, str | None, Exchange]:
        """
        Функция возвращает ключи в соответствии с биржей сигнала
        :return:
        """
        if self._secrets.exchange in [Exchange.BINANCE, Exchange.BINANCE.value]:
            if self._secrets.binance_api_key and self._secrets.binance_api_secret:
                return self._secrets.binance_api_key, self._secrets.binance_api_secret, None, self._secrets.exchange
            raise ValueError("No keys on binance excange!")

        elif self._secrets.exchange in [Exchange.BYBIT, Exchange.BYBIT.value]:
            if self._secrets.bybit_api_key and self._secrets.bybit_api_secret:
                return self._secrets.bybit_api_key, self._secrets.bybit_api_secret, None, self._secrets.exchange
            raise ValueError("No keys on bybit excange!")

        elif self._secrets.exchange in [Exchange.OKX, Exchange.OKX.value]:
            if self._secrets.okx_api_key and self._secrets.okx_api_secret:
                return self._secrets.okx_api_key, self._secrets.okx_api_secret, self._secrets.okx_api_pass, \
                    self._secrets.exchange
            raise ValueError("No keys on okx excange!")

        else:
            try:
                raise ValueError(f"Exchange was not defined by user: {self._secrets.exchange} ({type(self._secrets.exchange)}).")
            except:  # noqa
                raise ValueError(f"Exchange was not defined by user.")

    async def _send_alert(self, source: SignalDict) -> None:
        """ Function to send telegram alert. """
        try:
            text = f"""
<b>🤖 Внимание! На {source["ticker"].upper()} 5m вероятен отскок.</b>

1. Найдите силу по <a href='https://t.me/filipchuka/1023'>логике CDV.</a>
2. Определите уровни по <a href='https://t.me/filipchuka/994'>сетке Фибоначчи.</a>
3. Проанализируйте <a href='https://t.me/filipchuka/1049'>профиль объема на рост/падение.</a>
Соблюдайте риск менеджмент.
—

Created by Signal robot v2 | Filipchuk’s method ({source["strategy"]})
—

<i>🐧 Вернуться <a href='https://t.me/filipchuka/1023'>к содержанию тренинга.</a></i>
            """
            await AlertWorker.send(message=text, parse_mode="HTML")
        except Exception as e:
            await AlertWorker.error(f"Error while sending alert: {e}")
