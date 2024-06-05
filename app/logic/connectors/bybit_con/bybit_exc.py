from pybit.unified_trading import HTTP

from ..abstract import ABCExchange


class Bybit(ABCExchange):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.symbol: str = self._signal.ticker

        self.bybit: HTTP | None = None

    async def init_client(self) -> None:
        self.bybit = HTTP(
            api_key=self._api_key,
            api_secret=self._api_secret,
            testnet=False,
        )

    def process_signal(self) -> None:
        pass
