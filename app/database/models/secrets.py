__all__ = ["SecretsORM", ]

from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from ..enums import Exchange
from app.config import DB_VERSION


class SecretsORM(Base):
    """
    Модель cекретных данных в базе данных.
    """

    __tablename__ = f"secrets_table_{DB_VERSION}"

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
    okx_api_pass: Mapped[str] = mapped_column(nullable=True)

    # Состояние сигналов
    alerts: Mapped[bool] = mapped_column(nullable=True)
