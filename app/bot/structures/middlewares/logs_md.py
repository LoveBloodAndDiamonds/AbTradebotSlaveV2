from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message

from app.config import logger


def _hide_keys(data: str) -> str:
    """
    Функция прячет ключи из логов.
    :param data:
    :return:
    """
    try:
        splitted_data = data.split(" ")
        if splitted_data[0] in ["/key_bybit", "/secret_bybit", "/key_binance", "/secret_binance"]:
            data = splitted_data[0] + " " + "*" * len(splitted_data[1])
    except Exception as e:
        logger.error(f"Error while middleware logs: {e}")

    return data


class LogsMiddleware(BaseMiddleware):
    """This middleware logs users actions"""

    async def __call__(
            self,
            handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
            event: Message | CallbackQuery,
            data: dict,
    ) -> Any:
        """This method calls every update."""
        try:
            event_type = "Unknown"
            event_data = "Unknown"
            if isinstance(event, Message):
                event_type = "Msg"
                event_data = event.text.replace("\n", "<br>")

                if event_data is None:
                    try:
                        if event.photo[-1]:
                            event_data = "<Photo>"
                    except Exception as e:
                        logger.debug(f"Can not recognize input file: {e}")

                # Игнорируем логирование секретных данных
                _hide_keys(event_data)

            elif isinstance(event, CallbackQuery):
                event_type = "Clbck"
                event_data = event.data
            logger.debug(f"{event_type} frm {event.from_user.id}: {event_data}")

            return await handler(event, data)
        except Exception as e:
            logger.exception(f"Error handling event: {e}")
