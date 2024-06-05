import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import DATABASE_URL, logger
from app.database import Database, SecretsORM
from app.logic import Logic
from .handlers import register_commands, set_up_commands
from .structures import register_filters, register_middlewares


async def start_bot() -> None:
    """Функция запускает бота."""
    db: Database = await Database.create(database_url=DATABASE_URL)
    secrets: SecretsORM = await db.secrets_repo.get()

    bot = Bot(token=secrets.bot_token, default=DefaultBotProperties(parse_mode="HTML", link_preview_is_disabled=True))

    # Инициализируем главный объект логики, который отвечает за стратегии пользователя
    logic: Logic = Logic(secrets=secrets, db=db)
    asyncio.create_task(logic.start_logic())  # noqa

    # Создаем диспатчер
    dp = Dispatcher(storage=MemoryStorage())

    # Регистрируем команды
    register_commands(dp)

    # Регестрируем мидлвари
    register_middlewares(dp)

    # Регистрируем фильтры
    register_filters(dp, admin_id=secrets.admin_telegram_id)

    # Регестрируем команды
    await set_up_commands(bot)

    # Выводим сообщение о запуске бота
    logger.success(f"Bot https://t.me/{(await bot.get_me()).username} launched!")

    # Запуск бота
    await dp.start_polling(
        bot,
        allowed_updates=dp.resolve_used_update_types(),
        db=db,
        logic=logic
    )
