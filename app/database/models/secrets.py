__all__ = ["SecretsORM", ]

from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from ..enums import Exchange


class SecretsORM(Base):
    """
    Модель cекретных данных в базе данных.
    """

    __tablename__ = "secrets_table_204"  # change name to not enter to users servers and clear old tables

    id: Mapped[int] = mapped_column(primary_key=True, unique=True, default=1)

    # Настройки телеграм бота
    bot_token: Mapped[str] = mapped_column(nullable=True)
    admin_telegram_id: Mapped[int] = mapped_column(nullable=True)

    # Ключ лицензии
    license_key: Mapped[str] = mapped_column(nullable=True)

    # Выбранная биржа
    exchange: Mapped[Exchange] = mapped_column(nullable=True)

    # Апи ключи с бинанса
    binance_api_key: Mapped[str] = mapped_column(nullable=True)
    binance_api_secret: Mapped[str] = mapped_column(nullable=True)

    # Апи ключи с байбита
    bybit_api_key: Mapped[str] = mapped_column(nullable=True)
    bybit_api_secret: Mapped[str] = mapped_column(nullable=True)

    # Апи ключи с okx
    okx_api_key: Mapped[str] = mapped_column(nullable=True)
    okx_api_secret: Mapped[str] = mapped_column(nullable=True)
