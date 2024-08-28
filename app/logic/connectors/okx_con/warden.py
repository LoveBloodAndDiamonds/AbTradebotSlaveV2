import asyncio

from app.config import logger, WARDEN_TIMEOUT
from app.database import SecretsORM, Database
from .client import AsyncClient
from ..abstract import ABCPositionWarden
from ...utils import AlertWorker


class OKXWarden(ABCPositionWarden):

    def __init__(self, db: Database):
        self._db = db
        self._client: AsyncClient | None = None

    async def start_warden(self) -> None:
        """
        Функция запускает бесконечный цикл, в котором проверяются открытые позиции без стопов.
        :return:
        """
        logger.success("OKX warden started")
        prev_iteration_positions: list[dict] = []

        while True:
            secrets: SecretsORM = await self._db.secrets_repo.get()
            if all([secrets.okx_api_key, secrets.okx_api_secret, secrets.okx_api_pass]):
                try:
                    # Инициализируем клиент
                    self._client = AsyncClient(
                        api_key=secrets.okx_api_key,
                        secret_key=secrets.okx_api_secret,
                        passphrase=secrets.okx_api_pass
                    )

                    # Получаем все открытые позиции и открытые ордера
                    # positions: dict = await client.get_open_positions(instType="SWAP")
                    positions: dict = await self._client.get_account_positions_risk(instType="SWAP")
                    positions: list[dict] = positions["data"][0]["posData"]
                    oco_orders: dict = await self._client.get_open_algo_orders(ordType="oco")
                    oco_orders: list[dict] = oco_orders["data"]
                    cond_orders: dict = await self._client.get_open_algo_orders(ordType="conditional")
                    cond_orders: list[dict] = cond_orders["data"]
                    orders: list[dict] = cond_orders + oco_orders

                    # Получаем позиции, которые нужно закрыть
                    curr_iteration_positions: list[dict] = self._check_positions_health(
                        orders=orders,
                        positions=positions)
                    if curr_iteration_positions:
                        logger.info(f"Find positions to w/o stop: {curr_iteration_positions}")

                    # Находим одинаковые элементы в последних итерациях
                    positions_to_close: list[dict] = self._find_common_elements(
                        prev_iteration=prev_iteration_positions,
                        curr_iteration=curr_iteration_positions)
                    if positions_to_close:
                        logger.warning(f"I should close positions: {positions_to_close}")

                    # Обновляем историю найденных позиций
                    prev_iteration_positions = curr_iteration_positions

                    # Закрываем позиции
                    await self._close_positions(positions_to_close)

                except Exception as e:
                    logger.exception(f"Error in okx warden: {e}")
            else:
                prev_iteration_positions.clear()
            await asyncio.sleep(WARDEN_TIMEOUT)

    def _check_positions_health(
            self,
            positions: list[dict],
            orders: list[dict]
    ) -> list[dict]:
        """
        Функция проверяет, чтобы на позиции обязательно стоял стоп-ордер.
        Возвращает список позииций, в которых стоп ордер не стоит.
        :param positions:
        :param orders:
        :return:
        """
        positions_to_close: list[dict] = []

        symbol_orders_types: dict[str, list[str]] = {}

        for order in orders:
            order_type: str | None = "sl" if order["slTriggerPx"] else "tp" if order["tpTriggerPxType"] else None
            if not order_type:
                continue
            if order["instId"] not in symbol_orders_types:
                symbol_orders_types[order["instId"]] = [order_type]
            else:
                symbol_orders_types[order["instId"]].append(order_type)

        for position in positions:
            # Проверка хотя бы какого-нибудь ордера на позиции, если ордеров совсем нет -
            # то такую позицию надо закрыть
            if position["instId"] not in symbol_orders_types:
                positions_to_close.append(
                    {
                        "instId": position["instId"],
                    }
                )
                continue

            # Проверка типа ордеров
            for order_type in symbol_orders_types[position["instId"]]:
                if order_type == "sl":
                    break
            else:
                positions_to_close.append(
                    {
                        "instId": position["instId"],
                    }
                )

        return positions_to_close

    async def _close_positions(self, positions_to_close: list[dict]) -> None:
        """
        Функиця закрывает позиции и отменяет ордера.
        :param positions_to_close: [{'instID': 'MATIC-USDT-SWAP', 'notionalCcy': 50.0, 'side': 'buy'}]
        :return:
        """
        for p in positions_to_close:
            body: dict = dict(
                instId=p["instId"],
                mgnMode="cross",
                posSide="net",
                autoCxl=True
            )
            responce: dict = await self._client.close_position(body=body)
            # {'code': '0',
            # 'data': [{'clOrdId': '', 'instId': 'MATIC-USDT-SWAP', 'posSide': 'net', 'tag': ''}], 'msg': ''}

            if responce.get("code") == "0":
                logger.info(f"Close position w/o stop: {responce}")
                await AlertWorker.warning(
                    f"Позиция по {p['instId']} на okx.com была закрыта, потому что по ней не стоял стоп-лосс.")
            else:
                logger.error(f"Error while closing position w/o stop: {responce}")
                await AlertWorker.error(
                    f"Ошибка при закрытии позиции на okx.com {p}, на которой нет стоп-лосса: {responce}")

        # warn_text: str = "У Вас есть позиции без стоп-лосса по:\n"
        # for p in positions_to_close:
        #     warn_text += f"{p['instId']} в сторону {p['side']} размером {p['notionalCcy']}"
        # if positions_to_close:
        #     await AlertWorker.warning(message=warn_text)
