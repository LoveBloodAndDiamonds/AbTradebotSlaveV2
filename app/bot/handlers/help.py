from aiogram import types


async def help_command_handler(message: types.Message) -> types.Message:
    """/help command"""
    return await message.answer("""
/help - Список доступных команд
/status - Состояние бота, активные стратегии
/license - Состояние лицензии
/trade - Инструкция по запуску стратегии
/stop - Инструкция по остановке стратегий
/keys - Инструкция по установке API ключей
/exchange - Инструкция по выбору биржи
    """)
