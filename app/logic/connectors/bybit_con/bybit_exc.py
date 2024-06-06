from app.config import logger
from .client import AsyncClient
from .exchange_info import exchange_info
from ..abstract import ABCExchange
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

            return True

        except Exception as e:
            logger.exception(f"Error while process signal: {e}")
            await AlertWorker.send(f"Ошибка при обработке сигнала: {e}")
            return False

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
            logger.info(f"Позиция по {self.symbol} уже открыта.")
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
