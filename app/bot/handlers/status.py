from aiogram import types

from app.logic import Logic, UserStrategySettings


async def status_command_handler(message: types.Message, logic: Logic) -> types.Message:
    """/status command"""

    active_strategies: dict[str, UserStrategySettings] = logic.get_active_user_strategies()

    if active_strategies:
        text: str = "<b>Активные стратегии:</b>\n\n"
        command_to_relaunch: str = "\n<pre>/trade \n"

        for name, settings in active_strategies.items():
            text += (f"▫️ <b>{name}</b>:\n"
                     f"Риск {settings.risk_usdt}$, осталось "
                     f"{settings.trades_count if settings.trades_count else '∞'} сделок\n\n")
            command_to_relaunch += (f"{name} {settings.risk_usdt}$ "
                                    f"{settings.trades_count if settings.trades_count else ''}\n")
        command_to_relaunch += "</pre>"

        return await message.answer(text + command_to_relaunch)
    else:
        return await message.answer("❕ У Вас нет активных стратегий. Используйте команду /trade для запуска.")
