from aiogram import types
from aiogram.filters import CommandObject

from app.database import Database, SecretsORM, Exchange


async def exchange_command_handler(message: types.Message, command: CommandObject, db: Database) -> types.Message:
    """/exchange command"""
    secrets: SecretsORM = await db.secrets_repo.get()

    if not command.args:
        if not secrets.exchange:
            text: str = "‼️ Вы еще не выбрали биржу, обязательно сделайте это, иначе бот не будет работать.\n\n"
        else:
            text: str = f"✅ Выбранная Вами биржа: {secrets.exchange.value}\n\n"
        text += ("Чтобы выбрать биржу, необходимо вставить ее название через пробел после команды, "
                 "например:\n<blockquote>/exchange binance</blockquote>\n\n"
                 f"Доступные биржи: {', '.join([e.value for e in Exchange])}")
        return await message.answer(text)

    try:
        exchange: str = command.args.strip().upper()
        exchange: Exchange = Exchange[exchange]
        secrets.exchange = exchange
        await db.secrets_repo.update(secrets)
        return await message.answer(f"✅ Биржа обновлена на {exchange.value}")
    except KeyError:
        return await message.answer(f"Вы указали биржу, которой нет в списке: {', '.join([e.value for e in Exchange])}")
