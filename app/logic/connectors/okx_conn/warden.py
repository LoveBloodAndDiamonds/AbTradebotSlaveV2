from app.database import Database
from ..abstract import ABCPositionWarden


class OKXWarden(ABCPositionWarden):

    def __init__(self, db: Database):
        self._db = db

    def start_warden(self) -> None:
        pass  # todo
