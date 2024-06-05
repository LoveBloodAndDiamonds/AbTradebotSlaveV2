from aiogram import types


async def start_command_handler(message: types.Message) -> types.Message:
    """/start command"""
    return await message.answer("""
Привет! 
Ты попал в бота для торговли по сигналам @filipchuka.
Чтобы посмотреть список доступных комманд - введи /help    
    """)
