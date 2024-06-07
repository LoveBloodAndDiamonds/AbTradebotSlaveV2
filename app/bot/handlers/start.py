from aiogram import types


async def start_command_handler(message: types.Message) -> types.Message:
    """/start command"""
    return await message.answer("""
Здравствуйте! 👋
Этот бот выступает в качестве панели управления для торговли по сигналам @filipchuka.
Чтобы посмотреть список доступных комманд - введите комманду /help    
    """)
