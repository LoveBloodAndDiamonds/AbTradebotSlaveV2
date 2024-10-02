import asyncio
from typing import Optional

from binance import AsyncClient
from binance.enums import *

from app import config
from app.config import log_args, logger, log_errors
from .exchange_info import exchange_info
from .breakeven import BinanceBreakevenWebSocket
from ..abstract import ABCExchange
from ...utils import AlertWorker
from ...schemas import BreakevenType, BreakevenTask


class Binance(ABCExchange):
    rW: dict[str, int] = {"recvWindow": 1_000}  # the number of milliseconds the request is valid for

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.binance: AsyncClient | None = None

    async def _init_client(self) -> None:
        """
        Функция инициализирует клиент для работы с биржей.
        :return:
        """
        self.binance = await AsyncClient.create(
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
            await self.binance.futures_cancel_all_open_orders(symbol=self.symbol)

            # Определяем сторону позиции
            self._define_position_side()

            # Определяем последнюю цену тикера
            await self._define_ticker_last_price()

            # Определеяем размер позиции исходя из рисков юзера
            self._define_position_quantity()

            # Создаем аргументы для всех оредров
            market_order: dict | bool = await self._create_order(
                self._create_order_kwargs(
                    type_=FUTURE_ORDER_TYPE_MARKET,
                    quantity=self.quantity,
                    side=self.side,
                ))

            if not market_order:
                return False

            # Ждем пока ордер заполнится
            await self._w8_till_order_filled(order_id=market_order["orderId"])

            _: dict | bool = await self._create_order(
                self._create_order_kwargs(
                    type_=FUTURE_ORDER_TYPE_STOP_MARKET,
                    side=SIDE_BUY if self.side == SIDE_SELL else SIDE_SELL,
                    stop_price=self._signal.stop_loss,
                    close_position=True
                ))

            _: dict | bool = await self._create_order(
                self._create_order_kwargs(
                    type_=FUTURE_ORDER_TYPE_TAKE_PROFIT_MARKET,
                    side=SIDE_BUY if self.side == SIDE_SELL else SIDE_SELL,
                    stop_price=self._signal.take_profit,
                    close_position=True
                )
            )

        except Exception as e:
            logger.exception(f"Error while process signal: {e}")
            await AlertWorker.error(f"Ошибка при обработке сигнала: {e}")
            return False
        else:
            await BinanceBreakevenWebSocket(
                task=BreakevenTask(
                    ticker=self.symbol,
                    stop_loss=self._signal.stop_loss,
                    take_profit=self._signal.take_profit,
                    plus_breakeven=self._signal.plus_breakeven,
                    minus_breakeven=self._signal.minus_breakeven,
                    callback=self._handle_breakeven_event,
                    meta="binance breakeven task"
                ),
            ).run()

            return True
        finally:
            await self.binance.close_connection()

    @log_errors
    async def _w8_till_order_filled(self, order_id: int) -> None:
        """
        Функция ждет, пока ордер заполнится.
        :param order_id:
        :return:
        """
        for _ in range(50):
            try:
                try:
                    order: dict = await self.binance.futures_get_order(symbol=self.symbol, orderId=order_id)
                except Exception as e:
                    logger.error(f"Can't get order status: {e}")
                    continue

                if order["status"] == "FILLED":
                    logger.info(f"Order filled: {order}")
                    await AlertWorker.info(f"Ордер по {self.symbol} заполнен.")
                    return
                elif order["status"] in ["CANCELED", "PENDING_CANCEL", "REJECTED", "EXPIRED"]:
                    raise Exception(f"Order status is bad: {order['status']}")
            finally:
                await asyncio.sleep(0.2)
        else:
            raise Exception(f"Cant w8 more order filled...")

    @log_errors
    async def _handle_breakeven_event(self, be_type: BreakevenType) -> None:
        """
        Функция ловит каллбек, когда BinanceBreakevenWebSocket находит момент, когда нужно переставить позицию
        в безубыток.
        :param be_type: Исходя из этого параметра понятно какой тип ордера выставлять.
        :return:
        """
        # Need to renew instance of client to avoid RuntimeError: Session is closed
        self.binance = await AsyncClient.create(
            api_key=self._api_key,
            api_secret=self._api_secret
        )

        try:
            await AlertWorker.warning(f"Пытаюсь переставить безубыток на стратегии {self._signal.strategy}. "
                                      f"Дождитесь сообщения об успешном создании ордера.")
            position_info = await self.binance.futures_position_information(symbol=self.symbol)
            position_amount: float = float(position_info[0]["positionAmt"])
            if position_amount == 0:
                return await AlertWorker.error(f"Позиция по {self._signal.strategy} уже закрыта.")

            # Определяем стороны поизции и сторону для безубытка
            position_side: str = SIDE_BUY if position_amount > 0 else SIDE_SELL
            be_side: str = SIDE_BUY if position_side == SIDE_SELL else SIDE_SELL

            # Считаем цену безубытка
            if position_side == SIDE_SELL:
                be_price: float = float(position_info[0]["entryPrice"]) * (1 - config.BREAKEVEN_STEP_PERCENT / 100)
            elif position_side == SIDE_BUY:
                be_price: float = float(position_info[0]["entryPrice"]) * (1 + config.BREAKEVEN_STEP_PERCENT / 100)

            # Создаем kwargs для ордера
            if be_type == BreakevenType.MINUS:
                be_kwargs: dict = self._create_order_kwargs(
                    type_=FUTURE_ORDER_TYPE_TAKE_PROFIT_MARKET,
                    side=be_side,
                    stop_price=be_price,
                    close_position=True
                )
            elif be_type == BreakevenType.PLUS:
                be_kwargs: dict = self._create_order_kwargs(
                    type_=FUTURE_ORDER_TYPE_STOP_MARKET,
                    side=be_side,
                    close_position=True,
                    stop_price=be_price
                )

            # Исполняем ордер
            await self._create_order(be_kwargs)
        except Exception:
            raise
        finally:
            await self.binance.close_connection()

    async def _is_available_to_open_position(self) -> bool:
        """
        Функция определяет можно ли открыть позицию сейчас.
        :return:
        """
        position_info = await self.binance.futures_position_information(symbol=self.symbol)
        if float(position_info[0]["positionAmt"]) != 0:
            logger.info(f"Position on {self.symbol} already opened.")
            return False
        return True

    async def _define_ticker_last_price(self) -> None:
        """
        Функция получает и возвращает последнюю цену монеты для определения размера позиции.
        :return:
        """
        futures_ticker: dict = await self.binance.futures_symbol_ticker(symbol=self.symbol)
        self.last_price = float(futures_ticker["price"])

    def _define_position_side(self) -> None:
        """
        Функция определяет сторону позиции исходя из положения тейка и стопа.
        :return:
        """
        if self._signal.take_profit > self._signal.stop_loss:
            self.side = SIDE_BUY
        elif self._signal.take_profit < self._signal.stop_loss:
            self.side = SIDE_SELL
        else:
            raise ValueError("Can not define position side")

    @log_args
    async def _create_order(self, order: dict) -> dict | bool:
        """
        Функция создает ордер.
        Возвращает dict, если ордер успешно создан, и False - если есть ошибка.
        {'orderId': 57899850340, 'symbol': 'XRPUSDT', 'status': 'NEW',
          'clientOrderId': 'wNFWvZUcxBpajxwOoUhcB7', 'price': '0.0000', 'avgPrice': '0.00', 'origQty': '70.3',
          'executedQty': '0.0', 'cumQty': '0.0', 'cumQuote': '0.00000', 'timeInForce': 'GTC', 'type': 'MARKET',
          'reduceOnly': False, 'closePosition': False, 'side': 'BUY', 'positionSide': 'BOTH',
          'stopPrice': '0.0000', 'workingType': 'CONTRACT_PRICE', 'priceProtect': False, 'origType': 'MARKET',
          'priceMatch': 'NONE', 'selfTradePreventionMode': 'NONE', 'goodTillDate': 0,
          'updateTime': 1717597474833}
        :param order:
        :return:
        """
        r: dict = await self.binance.futures_create_order(**order)
        if r.get("status") == "NEW":
            logger.debug(f"Order created: {r}")

            await AlertWorker.success(f"Создан {r['type']} ордер на {r['symbol']}")

            if r["type"] != "MARKET":
                return r

            # Ждем пока ордер заполниться, чтобы вернуть цену входа и убедиться, что ордер был открыт
            while r.get("status", "") != "FILLED":
                r = await self.binance.futures_get_order(symbol=self.symbol, orderId=r["orderId"])
                if r.get("status", "") not in ["FILLED", "NEW", "PARTIALLY_FILLED"]:
                    logger.error(f"Order {r} was canceled or anything else")
                    return False
                await asyncio.sleep(0.2)
            logger.info(f"Order filled: {r}")
            return r
        else:
            logger.error(f"Error while creating order: {r}")
            await AlertWorker.error(f"Ошибка при создании ордера: {r}")
            return False

    def _define_position_quantity(self) -> None:
        """
        Функция определяет размер позиции.
        :return:
        """
        if self.side == SIDE_BUY:
            percents_to_stop: float = 1 - self._signal.stop_loss / self.last_price
        elif self.side == SIDE_SELL:
            percents_to_stop: float = self.last_price / self._signal.stop_loss - 1
        else:
            raise ValueError("Wrong position side")
        self.quantity = self._user_strategy.risk_usdt / (percents_to_stop * self.last_price)

    def _create_order_kwargs(self,
                             type_: str,
                             side: str,
                             quantity: Optional[float] = 0,
                             reduce_only: Optional[bool] = False,
                             close_position: Optional[bool] = False,
                             price: Optional[float] = 0,
                             stop_price: Optional[float] = 0,
                             time_in_force: Optional[str] = TIME_IN_FORCE_GTC,
                             callback_rate: Optional[float] = 0.0,
                             client_order_id: Optional[str] = None,
                             ) -> dict:
        kwargs = {
            'symbol': self.symbol,
            'type': type_,
            'side': side
        }

        if client_order_id:
            kwargs['newClientOrderId'] = client_order_id

        # Here will be one place where price and qty rounds
        if quantity:
            quantity = abs(exchange_info.round_quantity(self.symbol, quantity))
        if price:
            price = exchange_info.round_price(self.symbol, price)
        if stop_price:
            stop_price = exchange_info.round_price(self.symbol, stop_price)

        if type_ == FUTURE_ORDER_TYPE_MARKET:
            kwargs['quantity'] = str(quantity)

        elif type_ == FUTURE_ORDER_TYPE_LIMIT:
            kwargs['price'] = str(price)
            kwargs['reduceOnly'] = str(reduce_only)
            kwargs['timeInForce'] = str(time_in_force)
            kwargs['quantity'] = str(quantity)

        elif type_ == FUTURE_ORDER_TYPE_STOP:
            kwargs['quantity'] = str(quantity)
            kwargs['stopPrice'] = str(stop_price)
            kwargs['price'] = str(price)

        elif type_ == FUTURE_ORDER_TYPE_STOP_MARKET:
            kwargs['stopPrice'] = str(stop_price)
            kwargs['closePosition'] = str(close_position)
            kwargs['quantity'] = str(quantity)

        elif type_ == FUTURE_ORDER_TYPE_TAKE_PROFIT_MARKET:
            kwargs['stopPrice'] = str(stop_price)
            kwargs['closePosition'] = str(close_position)

        elif type_ == FUTURE_ORDER_TYPE_TRAILING_STOP_MARKET:
            kwargs['reduceOnly'] = str(reduce_only)
            kwargs['quantity'] = str(quantity)
            kwargs['activationPrice'] = str(price)
            kwargs['callbackRate'] = str(callback_rate)

        return kwargs
