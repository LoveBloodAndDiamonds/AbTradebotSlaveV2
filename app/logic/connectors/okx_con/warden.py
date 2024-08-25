from app.database import Database
from ..abstract import ABCPositionWarden


class OKXWarden(ABCPositionWarden):

    def __init__(self, db: Database):
        self._db = db

    def start_warden(self) -> None:
        """
        Функция запускает бесконечный цикл, в котором проверяются открытые позиции без стопов.
        :return:
        """
        pass  # todo
