__all__ = ["SecretsORM", ]

from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class SecretsORM(Base):
    """
    Модель cекретных данных в базе данных.
    """

    __tablename__ = "secrets_table"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True, default=1)

    # Настройки телеграм бота
    bot_token: Mapped[str] = mapped_column(nullable=True)
    admin_telegram_id: Mapped[int] = mapped_column(nullable=True)

    # Ключ лицензии
    license_key: Mapped[str] = mapped_column(nullable=True)

    # Апи ключи с бинанса
    binance_api_key: Mapped[str] = mapped_column(nullable=True)
    binance_api_secret: Mapped[str] = mapped_column(nullable=True)

    # Апи ключи с байбита
    bybit_api_key: Mapped[str] = mapped_column(nullable=True)
    bybit_api_secret: Mapped[str] = mapped_column(nullable=True)
