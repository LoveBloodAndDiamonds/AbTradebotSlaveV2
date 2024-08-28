from app.config import logger, BREAKEVEN_STEP_PERCENT
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

        except Exception as e:
            logger.exception(f"Error while process signal: {e}")
            await AlertWorker.send(f"Ошибка при обработке сигнала по {self.symbol}: {e}")
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

    async def _handle_breakeven_event(self, be_type: BreakevenType) -> None:
        """ Функция принимает каллбек для события, когда нужно переставить безубыток. """
        try:
            await AlertWorker.warning(f"Пытаюсь переставить безубыток на стратегии {self._signal.strategy}. "
                                      f"Дождитесь сообщения об успешном создании ордера.")

            # Получаем информацию о текущей позиции
            position: dict = await self.okx.get_open_positions(instId=self.symbol)
            position: dict = position["data"][0]

            # from pprint import pp
            # pp(position)

            # Проверяем, возможно позиция уже закрыта
            if not position["pos"]:
                logger.info(f"Position on {self.symbol} already closed.")
                return

            side = "sell" if float(position["pos"]) < 0 else "buy" if float(position["pos"]) > 0 else \
                f"pos={position['pos']}"

            if side == "sell":
                be_price: float = float(position["avgPx"]) * (1 - BREAKEVEN_STEP_PERCENT / 100)
            elif side == "buy":
                be_price: float = float(position["avgPx"]) * (1 + BREAKEVEN_STEP_PERCENT / 100)
            else:
                raise ValueError("Wrong position side.")
            be_price: float = exchange_info.round_price(self.symbol, be_price)

            body: dict = dict(
                instId=self.symbol,
                tdMode="cross",
                side="sell" if side == "buy" else "buy",
                reduceOnly=True,
                ordType="conditional",  # or 'oco' idk
                closeFraction="1",  # maybe it will not work becouse it was already placed 1 sl/tp order,
            )

            if be_type == BreakevenType.PLUS:
                # move stop
                body["slOrdKind"] = "condition"
                body["slTriggerPx"] = be_price
                body["slOrdPx"] = -1
            elif be_type == BreakevenType.MINUS:
                # move tp
                body["tpOrdKind"] = "condition"
                body["tpTriggerPx"] = be_price
                body["tpOrdPx"] = -1

            responce: dict = await self.okx.place_algo_order(body=body)

            if responce.get("code") != "0":
                logger.exception(f"Error while opening order on okx.com: {responce}")
                await AlertWorker.error(f"Произошла ошибка при переставлении безубытка на okx.com: {responce}")
                raise Exception()
            else:
                await AlertWorker.success(f"Переставлен ордер в безубыток по {self.symbol} на цену {be_price}")

        except Exception as e:
            logger.exception(e)
            await AlertWorker.error(f"Произошла ошибка при переставлении безубытка на okx.com: {e}")

    async def _is_available_to_open_position(self) -> bool:
        """
        Функция определяет можно ли открыть позицию сейчас.
        :return:
        """
        positions: dict = await self.okx.get_open_positions(instId=self.symbol)
        # logger.debug("--posmark--")
        # logger.debug(positions)
        try:
            if positions["data"][0]["avgPx"]:
                logger.info(f"Position on {self.symbol} already opened.")
                return False
            return True
        except IndexError:
            raise Exception(f"okx.com return invalid data: {positions}")

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
            posSide="net",
            sz=abs(exchange_info.round_quantity(symbol=self.symbol, quantity=self.quantity)),
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

        responce: dict = await self.okx.place_order(body)

        if responce.get("code") != "0":
            raise Exception(f"Error while opening order on okx.com: {responce}")
        else:
            await AlertWorker.success(f"Открыт ордер по {self.symbol} на okx.com размером "
                                      f"{body['sz']} в сторону {body['side']}")
        return responce

