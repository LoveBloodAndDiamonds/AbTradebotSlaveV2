__all__ = ["register_middlewares", ]

from aiogram import Dispatcher

from .logs_md import LogsMiddleware


def register_middlewares(dp: Dispatcher) -> None:
    """
    Регистрирует мидлвари.
    :param dp:
    :return:
    """
    # Регестрируем мидлвари
    for mv in [LogsMiddleware()]:
        dp.message.middleware(mv)
        dp.callback_query.middleware(mv)
