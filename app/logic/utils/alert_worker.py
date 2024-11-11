from typing import Optional, Literal

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties

from app.config import logger
from app.database import SecretsORM


class AlertWorker:
    __BOT: Bot
    __ADMIN_ID: int

    @classmethod
    def init(cls, secrets: SecretsORM) -> None:
        """
        Функция инициализирует обьекты бота и телеграм айди пользователя, чтобы
        в дальнейшем отправлять ему сообщения.
        :param secrets: Секретные данные пользователя
        :return:
        """
        cls.__BOT_TOKEN: str = secrets.bot_token
        cls.__BOT: Bot = Bot(
            token=cls.__BOT_TOKEN,
            default=DefaultBotProperties(parse_mode="HTML", link_preview_is_disabled=True)
        )
        cls.__ADMIN_ID: int = secrets.admin_telegram_id

    @classmethod
    async def send(cls, message: str, parse_mode: Optional[Literal["HTML"]] = None) -> None:
        """
        Функция отправляет сообщение пользователю.
        :param message: Текст, который нужно отправить.
        :param parse_mode: Какой parse_mode использовать
        :return:
        """
        try:
            await cls.__BOT.send_message(
                chat_id=cls.__ADMIN_ID,
                text=message,
                parse_mode=parse_mode
            )
            logger.debug(f"Alert '{message}' was sent")
        except Exception as e:
            logger.error(f"Error while sending telegram alert: {e}")

    @classmethod
    async def success(cls, message: str) -> None:
        return await cls.send(f"✅ {message}")

    @classmethod
    async def error(cls, message: str) -> None:
        return await cls.send(f"‼️ {message}")

    @classmethod
    async def warning(cls, message: str) -> None:
        return await cls.send(f"⚠️ {message}")

    @classmethod
    async def info(cls, message: str) -> None:
        return await cls.send(f"❕ {message}")
