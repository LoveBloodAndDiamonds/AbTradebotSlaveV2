from app.config import logger
from .breakeven import OKXBreakevenWebSocket
from .client import AsyncClient
from .exchange_info import exchange_info
from ..abstract import ABCExchange
from ...schemas import BreakevenType, BreakevenTask
from ...utils import AlertWorker


class OKX(ABCExchange):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.symbol: str = self._signal.ticker.split("USDT")[0] + "-USDT-SWAP"

        self.okx: AsyncClient | None = None

    async def _init_client(self) -> None:
        """
        Функция инициализирует клиент биржи.
        :return:
        """
        self.okx = AsyncClient(api_key=self._api_key, secret_key=self._api_secret, passphrase=self._api_pass)

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
            await self.okx.cancel_all_open_orders(instId=self.symbol)

            # Определяем сторону позиции
            self._define_position_side()

            # Определяем последнюю цену тикера
            await self._define_ticker_last_price()

            # Определеяем размер позиции исходя из рисков юзера
            self._define_position_quantity()

            # Открываем маркет ордер
            await self._create_market_order()

            # Открывем тейк-профит

            # Открываем стоп-лосс

        except Exception as e:
            logger.exception(f"Error while process signal: {e}")
            await AlertWorker.send(f"Ошибка при обработке сигнала: {e}")
            return False

        else:
            await OKXBreakevenWebSocket(
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

    async def _handle_breakeven_event(self, be_type: BreakevenType):
        """ Функция принимает каллбек для события, когда нужно переставить безубыток. """
        await AlertWorker.warning(f"Пытаюсь переставить безубыток на стратегии {self._signal.strategy}. "
                                  f"Дождитесь сообщения об успешном создании ордера.")
        # todo

    async def _is_available_to_open_position(self) -> bool:
        """
        Функция определяет можно ли открыть позицию сейчас.
        :return:
        """
        positions: dict = await self.okx.get_open_positions(instId=self.symbol)
        if positions["data"][0]["margin"]:
            logger.info(f"Position on {self.symbol} already opened.")
            return False
        return True

    def _define_position_side(self) -> None:
        """
        Функция определяет сторону позиции исходя из положения тейка и стопа.
        :return:
        """
        if self._signal.take_profit > self._signal.stop_loss:
            self.side = "buy"
        elif self._signal.take_profit < self._signal.stop_loss:
            self.side = "sell"
        else:
            raise ValueError("Can not define position side")

    async def _define_ticker_last_price(self) -> None:
        """
        Функция получает и возвращает последнюю цену монеты для определения размера позиции.
        :return:
        """
        ticker: dict = await self.okx.get_last_price(instId=self.symbol)
        self.last_price = float(ticker["data"][0]["last"])

    def _define_position_quantity(self) -> None:
        """
        Функция определяет размер позиции.
        :return:
        """
        if self.side == "buy":
            percents_to_stop: float = 1 - self._signal.stop_loss / self.last_price
        elif self.side == "sell":
            percents_to_stop: float = self.last_price / self._signal.stop_loss - 1
        else:
            raise ValueError("Wrong position side")
        self.quantity = self._user_strategy.risk_usdt / (percents_to_stop * self.last_price)

    async def _create_market_order(self) -> dict:
        """
        Функция создает рыночный ордер.

        :raises: Exception, если произошла ошибка при создании ордера.
        :return:
        """
        body = dict(
            instId=self.symbol,
            ordType="market",
            side=self.side,
            tdMode="cross",
            sz=exchange_info.round_quantity(symbol=self.symbol, quantity=self.quantity),
            attachAlgoOrds=[
                dict(
                    tpOrdKind="condition",
                    tpTriggerPx=self._signal.take_profit,
                    tpOrdPx=-1,  # If the price is -1, take-profit will be executed at the market price.
                ),
                dict(
                    slOrdKind="condition",
                    slTriggerPx=self._signal.stop_loss,
                    slOrdPx=-1,  # If the price is -1, stop-loss will be executed at the market price.
                )
            ]
        )

        return await self.okx.place_order(body)
