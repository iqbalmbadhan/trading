"""Phase 6: kill switch blocks all order placement."""

from app.exchanges.base import Ticker
from app.exchanges.paper import PaperExchange
from app.execution.paper_executor import PaperExecutor
from app.risk.kill_switch import KillSwitch
from app.strategies.base import Signal, SignalSide


class FakeFlagStore:
    def __init__(self) -> None:
        self._d: dict[str, str] = {}

    def set(self, key: str, value: str):
        self._d[key] = value

    def delete(self, key: str):
        self._d.pop(key, None)

    def exists(self, key: str) -> int:
        return 1 if key in self._d else 0

    def get(self, key: str):
        return self._d.get(key)


def _price(p: float):
    async def _src(symbol: str) -> Ticker:
        return Ticker(symbol=symbol, bid=p, ask=p, last=p)

    return _src


def test_trip_clear_and_reason():
    ks = KillSwitch(FakeFlagStore())
    assert not ks.is_active()
    ks.trip("daily loss limit")
    assert ks.is_active() and ks.reason() == "daily loss limit"
    ks.clear()
    assert not ks.is_active() and ks.reason() is None


async def test_executor_blocks_orders_when_tripped():
    ks = KillSwitch(FakeFlagStore())
    ex = PaperExchange(_price(100.0), starting_cash=1000.0, slippage_bps=0.0)
    executor = PaperExecutor(ex, kill_switch=ks)
    sig = Signal(ts=1, symbol="BTC/USDT", side=SignalSide.BUY, qty=1.0)

    ks.trip("manual")
    blocked = await executor.execute(sig)
    assert blocked.order is None
    assert blocked.skipped_reason == "kill switch active"
    assert "BTC" not in await ex.fetch_balance()

    ks.clear()
    allowed = await executor.execute(sig)
    assert allowed.order is not None
    assert (await ex.fetch_balance())["BTC"] == 1.0
