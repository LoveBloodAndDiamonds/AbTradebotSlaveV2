from aiogram import types
from aiogram.filters import CommandObject

from app.database import Database, SecretsORM


async def alerts_command_handler(message: types.Message, command: CommandObject, db: Database) -> types.Message:
    """/alerts command"""
    secrets: SecretsORM = await db.secrets_repo.get()

    if not command.args:
        return await message.answer(
            f"Текущее состояние сигналов: {'✅ Вкл.' if secrets.alerts else '❌ Выкл.'}\n\n"
            f"Чтобы включить сигналы, введите:\n"
            "<blockquote>/alerts on</blockquote>\n"
            "Чтобы отключить сигналы, введите:\n"
            "<blockquote>/alerts off</blockquote>\n"
        )

    try:
        state: str = command.args.strip().lower()
        if state == "on":
            secrets.alerts = True
            await db.secrets_repo.update(secrets)
            return await message.answer(f"✅Сигналы включены.")
        elif state == "off":
            secrets.alerts = False
            await db.secrets_repo.update(secrets)
            return await message.answer(f"✅Сигналы выключены.")
        else:
            raise ValueError("Неверный аргумент, доступно только 'on' или 'off'")
    except Exception as e:
        return await message.answer(f"🛑 Ошибка при остановке стратегии: {e}")
