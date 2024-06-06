"""
Файл содержить в себе настройки логирования.
"""

import sys

from loguru import logger

from ._paths import LOGS_FOLDER_PATH

# Настройки логирования
logger.remove()

# Логирование в файл
for level in ["ERROR", "INFO", "DEBUG"]:
    logger.add(f'{LOGS_FOLDER_PATH}/{level.lower()}.log', level=level,
               format="<white>{time: %d.%m %H:%M:%S.%f}</white> | "
                      "<level>{level}</level>| "
                      "|{name} {function} line:{line}| "
                      "<bold>{message}</bold>",
               rotation="5 MB",
               compression='zip')

# Логирование в консоль
logger.add(sys.stderr, level="DEBUG",
           format="<white>{time: %d.%m %H:%M:%S}</white>|"
                  "<level>{level}</level>|"
                  "<bold>{message}</bold>")


def log_args(func):
    """
    Декоратор для логирования получаемых и возвращаемых аргументов.
    :param func:
    :return:
    """

    def wrapper(*args, **kwargs):
        logger.debug(f"Функция {func.__name__} принимает: args={args}, kwargs={kwargs}")
        result = func(*args, **kwargs)
        if result:
            logger.debug(f"Функция {func.__name__} возвращает: {result}")
        return result

    return wrapper


def log_errors(func):
    """
    Декоратор для логирования ошибок в функции.
    :param func:
    :return:
    """

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.exception(f"Ошибка в функции {func.__name__}: {e}")
            raise e

    return wrapper
