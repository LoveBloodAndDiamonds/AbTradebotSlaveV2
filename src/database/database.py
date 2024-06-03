"""Database class with all-in-one features."""

from sqlalchemy.engine.url import URL
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine as _create_async_engine
from sqlalchemy.orm import sessionmaker

from .models import Base
from .repositories import SecretsRepository


def create_async_engine(url: URL | str) -> AsyncEngine:
    """Create async engine with given URL.
    :param url: URL to connect
    :return: AsyncEngine
    """
    return _create_async_engine(url=url, pool_pre_ping=True)


async def proceed_schemas(engine: AsyncEngine) -> None:
    """
    Create db tables
    :param engine:
    :return:
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def get_session_maker(engine: AsyncEngine = None) -> sessionmaker:
    """
    Creates sessionmaker.
    :param engine:
    :return:
    """
    return sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


class Database:
    """Database class."""

    def __init__(self, session_maker: sessionmaker) -> None:
        self.secrets_repo: SecretsRepository = SecretsRepository(session_maker=session_maker)

    @classmethod
    async def create(cls, database_url: str) -> object:
        """
        Метод создает проинициализированный экземпляр базы данных.
        Предварительно создавая таблицы в базе данных.
        :param database_url: URL адрес базы данных.
        :return: Объект базы данных.
        """
        db_engine: AsyncEngine = create_async_engine(url=database_url)
        await proceed_schemas(db_engine)
        session_maker: sessionmaker = get_session_maker(db_engine)

        return cls(session_maker)
