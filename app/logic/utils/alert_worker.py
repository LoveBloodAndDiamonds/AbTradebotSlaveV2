from aiogram import Bot
from aiogram.client.default import DefaultBotProperties

from app.database import SecretsORM
from app.config import logger


class AlertWorker:
    BOT: Bot
    ADMIN_ID: int

    @classmethod
    def init(cls, secrets: SecretsORM) -> None:
        """
        Функция инициализирует обьекты бота и телеграм айди пользователя, чтобы
        в дальнейшем отправлять ему сообщения.
        :param secrets: Секретные данные пользователя
        :return:
        """
        cls.BOT = Bot(
            token=secrets.bot_token,
            default=DefaultBotProperties(parse_mode="HTML", link_preview_is_disabled=True)
        )
        cls.ADMIN_ID = secrets.admin_telegram_id

    @classmethod
    async def send(cls, message: str) -> None:
        """
        Функция отправляет сообщение пользователю.
        :param message: Текст, который нужно отправить.
        :return:
        """
        await cls.BOT.send_message(
            chat_id=cls.ADMIN_ID,
            text=message
        )
        logger.debug(f"Alert {message} was sent")

    @classmethod
    async def success(cls, message: str) -> None:
        return await cls.send(f"✅ {message}")

    @classmethod
    async def error(cls, message: str) -> None:
        return await cls.send(f"‼️ {message}")

    @classmethod
    async def warning(cls, message: str) -> None:
        return await cls.send(f"⚠️ {message}")
