from datetime import datetime

from aiogram import types

from app.logic import Logic


async def license_command_handler(message: types.Message, logic: Logic) -> types.Message:
    """/license command"""
    try:
        license_key_expired_date: datetime = await logic.get_license_key_expired_date()
    except Exception as e:
        return await message.answer(f"Произошла ошибка: {e}")

    return await message.answer(f"Ваша лицензия действует до {license_key_expired_date} (UTC+0)")
