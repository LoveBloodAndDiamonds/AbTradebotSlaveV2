from aiogram import types
from aiogram.filters import CommandObject

from app.logic import Logic


async def stop_command_handler(message: types.Message, command: CommandObject, logic: Logic) -> types.Message:
    """/stop command"""

    if not command.args:
        return await message.answer(
            f"Чтобы остановить стратегию, необходимо ввести команду формата:\n"
            "<blockquote>/stop {НазваниеСтратегии}</blockquote>\n"
            "Если вы хотите остановить все стратегии, введите:\n"
            "<blockquote>/stop *</blockquote>\n"
        )

    strategy_name: str = command.args.strip()
    try:
        logic.remove_user_startegy(strategy_name=strategy_name, stop_all=strategy_name == "*")
    except Exception as e:
        return await message.answer(f"🛑 Ошибка при остановке стратегии: {e}")
    if strategy_name == "*":
        return await message.answer(f"✅ Все стратегии остановлены.")
    else:
        return await message.answer(f"✅ Стратегия {strategy_name} остановлена.")
