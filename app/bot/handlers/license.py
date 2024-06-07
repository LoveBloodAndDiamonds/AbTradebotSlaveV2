from datetime import datetime

from aiogram import types

from app.logic import Logic
from app.database import Database, SecretsORM


async def license_command_handler(message: types.Message, logic: Logic, db: Database) -> types.Message:
    """/license command"""
    try:
        license_key_expired_date: datetime = await logic.get_license_key_expired_date()
    except Exception as e:
        return await message.answer(f"🛑 Произошла ошибка: {e}")

    secrets: SecretsORM = await db.secrets_repo.get()

    return await message.answer(f"🔑 Ваш ключ лицензии: <code>{secrets.license_key}</code>\n"
                                f"Ваша лицензия действует до {license_key_expired_date} (UTC)")
