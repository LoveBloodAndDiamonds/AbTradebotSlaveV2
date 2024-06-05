from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import BotCommand

from .start import start_command_handler
from .help import help_command_handler
from .keys import keys_command_handler
from .license import license_command_handler
from .trade import trade_command_handler
from .stop import stop_command_handler
from .status import status_command_handler


bot_commands = (
    ("help", "Инструкция и список команд"),
    ("status", "Состояние робота"),
    ("license", "Состояние лицензии"),
    ("trade", "Запуск стратегии"),
    ("stop", "Остановить стратегию(и)"),
    ("keys", "Настройка API ключей")
)


def register_commands(dp: Dispatcher) -> None:
    """
    Функция регистрирует хендлеры для команд на диспатчер.
    :param dp:
    :return:
    """
    dp.message.register(start_command_handler, Command("start"))
    dp.message.register(help_command_handler, Command("help"))
    dp.message.register(keys_command_handler, Command(
        commands=["keys", "key_binance", "secret_binance", "key_bybit", "secret_bybit"]))
    dp.message.register(license_command_handler, Command("license"))
    dp.message.register(trade_command_handler, Command("trade"))
    dp.message.register(stop_command_handler, Command("stop"))
    dp.message.register(status_command_handler, Command("status"))


async def set_up_commands(bot: Bot) -> None:
    """Set up commands what user will see."""
    commands_for_bot = []
    for cmd in bot_commands:
        commands_for_bot.append(BotCommand(command=cmd[0], description=cmd[1]))
    await bot.set_my_commands(commands=commands_for_bot)
