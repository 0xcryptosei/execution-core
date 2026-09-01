from datetime import datetime, timezone
from decimal import Decimal

from execution_core.clock import FakeClock
from execution_core.engine import Engine, EngineContext, KillSwitch
from execution_core.events import Event
from execution_core.paper_broker import PaperBroker
from execution_core.types import Account, Intent, OrderType, RiskLimits, Side


def _event() -> Event:
    return Event(
        type="tick",
        instrument="BTC-USD",
        ts=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


class OnceStrategy:
    def __init__(self) -> None:
        self.calls = 0

    def propose(self, event: Event, ctx: EngineContext) -> Intent | None:
        self.calls += 1
        if self.calls > 1:
            return None
        return Intent(
            client_id="cli-1",
            instrument=event.instrument,
            side=Side.BUY,
            order_type=OrderType.MARKET,
            qty=Decimal("1"),
        )


class RepeatStrategy:
    def propose(self, event: Event, ctx: EngineContext) -> Intent:
        return Intent(
            client_id="cli-1",
            instrument=event.instrument,
            side=Side.BUY,
            order_type=OrderType.MARKET,
            qty=Decimal("1"),
        )


class BuyThenSellStrategy:
    def __init__(self) -> None:
        self.step = 0

    def propose(self, event: Event, ctx: EngineContext) -> Intent | None:
        if self.step == 0:
            self.step = 1
            return Intent(
                client_id="buy-1",
                instrument=event.instrument,
                side=Side.BUY,
                order_type=OrderType.MARKET,
                qty=Decimal("1"),
            )
        if self.step == 1:
            self.step = 2
            return Intent(
                client_id="sell-1",
                instrument=event.instrument,
                side=Side.SELL,
                order_type=OrderType.LIMIT,
                qty=Decimal("1"),
                limit_price=Decimal("40"),
            )
        return None


def _engine(
    strategy: object,
    *,
    limits: RiskLimits | None = None,
    kill_switch: KillSwitch | None = None,
    last_price: Decimal = Decimal("100"),
) -> Engine:
    clock = FakeClock(datetime(2026, 1, 1, tzinfo=timezone.utc))
    broker = PaperBroker(last_price=last_price, clock=clock)
    return Engine(
        limits or RiskLimits(),
        kill_switch or KillSwitch(),
        broker,
        strategy,
        clock,
        account=Account(account_id="acct-1", cash=Decimal("10000")),
    )


def test_dummy_strategy_places_once_and_updates_position() -> None:
    strategy = OnceStrategy()
    engine = _engine(strategy)

    fills = engine.on_event(_event())

    assert len(fills) == 1
    assert engine.positions[0].qty == Decimal("1")
    assert engine.account.cash == Decimal("9900")
    assert engine.on_event(_event()) == []


def test_duplicate_client_id_does_not_double_place() -> None:
    engine = _engine(RepeatStrategy())

    first = engine.on_event(_event())
    second = engine.on_event(_event())

    assert len(first) == 1
    assert second == []
    assert engine.positions[0].qty == Decimal("1")


def test_halt_blocks_new_orders() -> None:
    engine = _engine(OnceStrategy())
    engine.halt("manual")

    fills = engine.on_event(_event())

    assert fills == []
    assert engine._kill_switch.halted is True
    assert engine._kill_switch.reason == "manual"


def test_daily_loss_auto_halts() -> None:
    strategy = BuyThenSellStrategy()
    limits = RiskLimits(max_daily_loss=Decimal("50"))
    kill_switch = KillSwitch()
    engine = _engine(strategy, limits=limits, kill_switch=kill_switch)

    engine.on_event(_event())
    engine.on_event(_event())

    assert kill_switch.halted is True
    assert kill_switch.reason == "daily_loss"
    assert engine.on_event(_event()) == []
