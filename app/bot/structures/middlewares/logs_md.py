from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message

from app.config import logger


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
                event_data = event.text
                if event_data is None:
                    try:
                        if event.photo[-1]:
                            event_data = "<Photo>"
                    except Exception as e:
                        logger.debug(f"Can not recognize input file: {e}")
            elif isinstance(event, CallbackQuery):
                event_type = "Clbck"
                event_data = event.data
            logger.debug(f"{event_type} frm {event.from_user.id}: {event_data}")

            return await handler(event, data)
        except Exception as e:
            logger.exception(f"Error handling event: {e}")
