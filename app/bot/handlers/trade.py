from datetime import datetime

from aiogram import types
from aiogram.filters import CommandObject

from app.logic import Logic


async def trade_command_handler(message: types.Message, command: CommandObject, logic: Logic) -> types.Message:
    """/trade command"""
    try:
        license_key_expired_date: datetime = await logic.get_license_key_expired_date()
        if license_key_expired_date < datetime.utcnow():
            raise Exception("Ваша подписка истекла.")
    except Exception as e:
        return await message.answer(f"🛑 Произошла ошибка: {e}")

    if not command.args:
        return await message.answer(
            f"Чтобы запустить стратегию, нужно ввести команду формата:\n"
            "<blockquote>/trade {НазваниеСтратегии} {Риск}$ {КоличествоПозиций}</blockquote>\n\n"
            f"Количество позиций можно не указывать, в таком случае - страетгия будет "
            f"работать, пока Вы ее не остановите.\n\n"
            f"Например:\n"
            f"<blockquote>/trade btc1min 10$ 10</blockquote>\n\n"
            f"Или:\n"
            f"<blockquote>/trade eth5min 10$</blockquote>"
        )

    try:
        if len(command.args.split(" ")) == 3:
            strategy_name, risk_usdt, trades_count = command.args.split(" ")
        elif len(command.args.split(" ")) == 2:
            strategy_name, risk_usdt = command.args.split(" ")
            trades_count = None
        risk_usdt = float(risk_usdt.replace("$", "").strip())
    except Exception as e:
        return await message.answer(f"🛑 Ошибка при парсинге введеного сообщения: {e}")

    try:
        await logic.add_user_strategy(
            strategy_name=strategy_name,
            risk_usdt=risk_usdt,
            trades_count=int(trades_count) if trades_count else None
        )
    except Exception as e:
        return await message.answer(f"🛑 Ошибка при запуске стратегии: {e}")

    return await message.answer(
        f"✅ Стратегия {strategy_name} с риском {risk_usdt}$ на {trades_count if trades_count else '∞'} сделок добавлена.")
