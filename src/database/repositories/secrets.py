__all__ = ["SecretsRepository", ]

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from ..models import SecretsORM


class SecretsRepository:
    model = SecretsORM

    def __init__(self, session_maker: sessionmaker):
        self.session_maker = session_maker

    async def add(self, obj: model) -> None:
        """
        Создает запись модели в базе данных.
        :param obj: Объект, который нужно добавить.
        :return:
        """
        async with self.session_maker() as session:
            session.add(obj)
            await session.commit()

    async def get(self) -> model | None:
        """
        Возвращает модель с id=1 из базы данных, если она существуют.
        Если нет - то возвращает None.
        :return:
        """
        async with self.session_maker() as session:
            result = await session.execute(select(self.model).where(self.model.id == 1))
            return result.scalars().first()

    async def update(self, obj: model) -> None:
        """
        Обновляет модель в базе данных.
        :param obj: Измененный обьект, который нужно "слить" с тем, что уже есть в базе данных.
        :return:
        """
        async with self.session_maker() as session:
            await session.merge(obj)
            await session.commit()
