__all__ = ["register_filters", ]

from aiogram import Dispatcher

from .admin import AdminFilter


def register_filters(dp: Dispatcher, admin_id: str | int) -> None:
    """
    Функция регистрирует фильтры на все сообщения.
    :param admin_id:
    :param dp:
    :return:
    """
    dp.message.filter(AdminFilter(admin_id=admin_id))
