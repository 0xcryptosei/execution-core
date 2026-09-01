from datetime import datetime, timezone
from decimal import Decimal

from execution_core import Intent, RiskChecker, RiskLimits, check
from execution_core.engine import Engine
from execution_core.events import bar_event, tick_event
from execution_core.types import Account, OrderType, RiskDecision, Side


def test_risk_checker_matches_check_function() -> None:
    limits = RiskLimits(max_order_qty=Decimal("5"))
    checker = RiskChecker(limits)
    intent = Intent(
        client_id="cli-1",
        instrument="BTC-USD",
        side=Side.BUY,
        order_type=OrderType.MARKET,
        qty=Decimal("10"),
    )
    account = Account(account_id="acct-1", cash=Decimal("10000"))
    now = datetime.now(timezone.utc)

    plan = checker.evaluate(intent, account, [], 0, now)
    direct = check(intent, account, [], 0, now, limits)

    assert plan == direct
    assert plan.risk_decision is RiskDecision.RESIZE
    assert plan.qty == Decimal("5")


def test_tick_and_bar_event_factories() -> None:
    ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
    tick = tick_event("ETH-USD", ts=ts, price="2500")
    bar = bar_event("ETH-USD", ts=ts, open="2500", close="2510")

    assert tick.type == "tick"
    assert bar.type == "bar"
    assert tick.instrument == "ETH-USD"
    assert tick.payload["price"] == "2500"
    assert bar.payload["close"] == "2510"


def test_engine_exposes_halt_status() -> None:
    from execution_core.clock import FakeClock
    from execution_core.engine import KillSwitch
    from execution_core.paper_broker import PaperBroker

    clock = FakeClock(datetime(2026, 1, 1, tzinfo=timezone.utc))
    kill_switch = KillSwitch()
    engine = Engine(
        RiskLimits(),
        kill_switch,
        PaperBroker(last_price=Decimal("1"), clock=clock),
        _NullStrategy(),
        clock,
    )

    assert engine.halted is False
    assert engine.halt_reason is None

    engine.halt("manual")

    assert engine.halted is True
    assert engine.halt_reason == "manual"


class _NullStrategy:
    def propose(self, event: object, ctx: object) -> None:
        return None
