from app import config
from app.config import logger, log_errors
from .breakeven import BybitBreakevenWebSocket
from .client import AsyncClient
from .exchange_info import exchange_info
from ..abstract import ABCExchange
from ...schemas import BreakevenType, BreakevenTask
from ...utils import AlertWorker


class Bybit(ABCExchange):
    category: str = "linear"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.symbol: str = self._signal.ticker

        self.bybit: AsyncClient | None = None

    async def _init_client(self) -> None:
        """
        Функция инициализирует клиент биржи.
        :return:
        """
        self.bybit = await AsyncClient.create(
            api_key=self._api_key,
            api_secret=self._api_secret,
        )

    async def process_signal(self) -> bool:
        """
        Функция обрабатывает сигнал и создает ордера на бирже.
        При успешном исполнении ордеров возвращается True, при неуспешном - False
        :return:
        """
        try:
            # Инициализация клиента для работы с биржей
            await self._init_client()

            # Проверка на то, есть ли уже открытая позицичя по тикеру
            if not await self._is_available_to_open_position():
                return False

            # Отправляем лог, что начинается обработка стратегии
            await AlertWorker.warning(f"Запуск стратегии {self._signal.strategy}")

            # Отменяем все старые ордера, которые были на монете
            await self.bybit.cancel_all_orders(category=self.category, symbol=self.symbol)

            # Определяем сторону позиции
            self._define_position_side()

            # Определяем последнюю цену тикера
            await self._define_ticker_last_price()

            # Определеяем размер позиции исходя из рисков юзера
            self._define_position_quantity()

            # Открываем маркет ордер (байбит позволяет сразу указать стоп и тейк)
            await self._create_market_order()

        except Exception as e:
            logger.exception(f"Error while process signal: {e}")
            await AlertWorker.send(f"Ошибка при обработке сигнала: {e}")
            return False

        else:
            await BybitBreakevenWebSocket(
                task=BreakevenTask(
                    ticker=self.symbol,
                    stop_loss=self._signal.stop_loss,
                    take_profit=self._signal.take_profit,
                    plus_breakeven=self._signal.plus_breakeven,
                    minus_breakeven=self._signal.minus_breakeven,
                    callback=self._handle_breakeven_event
                ),
            ).run()

            return True

    @log_errors
    async def _handle_breakeven_event(self, be_type: BreakevenType):
        """
        Функция ловит каллбек, когда BybitBreakevenWebSocket находит момент, когда нужно переставить позицию
        в безубыток.
        :param be_type: Исходя из этого параметра понятно какой тип ордера выставлять.
        :return:
        """
        await AlertWorker.warning(f"Пытаюсь переставить безубыток на стратегии {self._signal.strategy}. "
                                  f"Дождитесь сообщения об успешном создании ордера.")
        position_info: dict = await self.bybit.get_position_info(
            category=self.category,
            symbol=self.symbol)
        one_way_position_info: dict = position_info["result"]["list"][0]
        position_amount: float = float(one_way_position_info["size"])

        if position_amount == 0:
            return await AlertWorker.error(f"Позиция по {self._signal.strategy} уже закрыта.")

        # Считаем цену безубытка
        if one_way_position_info["side"] == "Sell":
            be_price: float = float(one_way_position_info["avgPrice"]) * (1 - config.BREAKEVEN_STEP_PERCENT / 100)
        elif one_way_position_info["side"] == "Buy":
            be_price: float = float(one_way_position_info["avgPrice"]) * (1 + config.BREAKEVEN_STEP_PERCENT / 100)

        # Создаем kwargs для ордера
        if be_type == BreakevenType.MINUS:
            params = dict(
                category=self.category,
                symbol=self.symbol,
                takeProfit=str(exchange_info.round_price(self.symbol, be_price)),
            )
        elif be_type == BreakevenType.PLUS:
            params = dict(
                category=self.category,
                symbol=self.symbol,
                stopLoss=str(exchange_info.round_price(self.symbol, be_price)),
            )

        response: dict = await self.bybit.set_position_trading_stop(**params)

        if response.get("retMsg") == "OK":
            await AlertWorker.success(f"Открыт ордер по {self.symbol} для безубытка по цене {be_price}.")
        else:
            _: str = f"Error while creating order: {response}"
            logger.error(_)
            await AlertWorker.error(_)
            raise ConnectionError(_)

    async def _define_ticker_last_price(self) -> None:
        """
        Функция получает и возвращает последнюю цену монеты для определения размера позиции.
        :return:
        """
        futures_ticker: dict = await self.bybit.get_ticker(category=self.category, symbol=self.symbol)
        self.last_price = float(futures_ticker["result"]["list"][0]["lastPrice"])

    def _define_position_quantity(self) -> None:
        """
        Функция определяет размер позиции.
        :return:
        """
        if self.side == "Buy":
            percents_to_stop: float = 1 - self._signal.stop_loss / self.last_price
        elif self.side == "Sell":
            percents_to_stop: float = self.last_price / self._signal.stop_loss - 1
        else:
            raise ValueError("Wrong position side")
        self.quantity = self._user_strategy.risk_usdt / (percents_to_stop * self.last_price)

    def _define_position_side(self) -> None:
        """
        Функция определяет сторону позиции исходя из положения тейка и стопа.
        :return:
        """
        if self._signal.take_profit > self._signal.stop_loss:
            self.side = "Buy"
        elif self._signal.take_profit < self._signal.stop_loss:
            self.side = "Sell"
        else:
            raise ValueError("Can not define position side")

    async def _is_available_to_open_position(self) -> bool:
        """
        Функция определяет можно ли открыть позицию сейчас.
        :return:
        """
        position_info: dict = await self.bybit.get_position_info(
            category=self.category,
            symbol=self.symbol)
        one_way_position_info: dict = position_info["result"]["list"][0]

        if float(one_way_position_info["size"]) != 0:
            logger.info(f"Position on {self.symbol} already opened.")
            return False
        return True

    async def _create_market_order(self) -> dict:
        """
        Функция создает рыночный ордер.

        Пример успешного ответа при создании ордера:
        {'retCode': 0, 'retMsg': 'OK',
             'result': {'orderId': '09ba039f-75ca-4abb-afdc-5d7adca1196f', 'orderLinkId': ''}, 'retExtInfo': {},
             'time': 1717659435045}

        :raises: Exception, если произошла ошибка при создании ордера.
        :return:
        """
        params = dict(
            category=self.category,
            symbol=self.symbol,
            side=self.side,
            orderType="MARKET",
            takeProfit=str(exchange_info.round_price(self.symbol, self._signal.take_profit)),
            stopLoss=str(exchange_info.round_price(self.symbol, self._signal.stop_loss)),
            qty=str(exchange_info.round_quantity(self.symbol, self.quantity)))
        logger.debug(f"Try to open order with {params=}")

        responce = await self.bybit.place_order(**params)

        if responce.get("retMsg") == "OK":
            await AlertWorker.success(f"Открыт ордер по {self.symbol} размером {params['qty']},"
                                      f" take={params['takeProfit']}, stop={params['stopLoss']}")
            return responce
        else:
            logger.error(f"Error while creating order: {responce}")
            raise ConnectionError(f"Ошибка при создании ордера: {responce}")
