from typing import Union

from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery

from app.config import logger


class AdminFilter(BaseFilter):
    """Фильтр на чат с админом."""

    def __init__(self, admin_id: Union[str, list]):
        self.admin_id = admin_id

    async def __call__(self, message: Message | CallbackQuery) -> bool:
        if isinstance(self.admin_id, int | str):
            if str(message.from_user.id) == str(self.admin_id):
                return True
            else:
                logger.warning(f"Got message from non-admin: @{message.from_user.username} ({message.from_user.id})")
        else:
            if str(message.from_user.id) in self.admin_id:
                return True
            else:
                logger.warning(f"Got message from non-admin: @{message.from_user.username} ({message.from_user.id})")
