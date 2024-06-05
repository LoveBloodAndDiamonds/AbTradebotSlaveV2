from aiogram import Bot


class AlertWorker:
    BOT: Bot
    ADMIN_ID: int

    @classmethod
    def init_worker(cls, bot: Bot, admin_id: int | str) -> None:
        cls.BOT = bot
        cls.ADMIN_ID = admin_id

    @classmethod
    async def send_alert(cls, message: str) -> None:
        await cls.BOT.send_message(
            chat_id=cls.ADMIN_ID,
            text=message
        )
