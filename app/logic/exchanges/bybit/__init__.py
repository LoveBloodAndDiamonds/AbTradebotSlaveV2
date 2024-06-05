from typing import Optional

from app.config import log_args
from .exchange_info import exchange_info
from ..abstract import Exchange


class Binance(Exchange):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def handle_signal(self) -> None:
        pass
