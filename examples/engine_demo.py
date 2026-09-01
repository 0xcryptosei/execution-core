#!/usr/bin/env python3
"""Run the paper engine with a one-shot BUY strategy."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal

from execution_core import Engine, FakeClock, KillSwitch, PaperBroker, RiskLimits
from execution_core.engine import EngineContext
from execution_core.events import Event, tick_event
from execution_core.logging_config import configure_logging
from execution_core.types import Intent, OrderType, Side


class OneBuyStrategy:
    def __init__(self) -> None:
        self._done = False

    def propose(self, event: Event, ctx: EngineContext) -> Intent | None:
        del ctx
        if self._done:
            return None
        self._done = True
        return Intent(
            client_id="engine-demo-1",
            instrument=event.instrument,
            side=Side.BUY,
            order_type=OrderType.MARKET,
            qty=Decimal("1"),
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the paper execution engine.")
    parser.add_argument("--fake-clock", action="store_true")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    configure_logging(args.log_level)

    clock = (
        FakeClock(datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc))
        if args.fake_clock
        else FakeClock(datetime.now(timezone.utc))
    )
    broker = PaperBroker(last_price=Decimal("50000"), clock=clock)
    engine = Engine(
        RiskLimits(max_order_qty=Decimal("10")),
        KillSwitch(),
        broker,
        OneBuyStrategy(),
        clock,
    )

    for event in (
        tick_event("BTC-USD", ts=clock.now()),
        tick_event("BTC-USD", ts=clock.now()),
    ):
        fills = engine.on_event(event)
        for fill in fills:
            print(f"fill: {fill.side.value} {fill.qty} @ {fill.price}")

    print(f"halted={engine.halted} reason={engine.halt_reason}")
    if engine.positions:
        pos = engine.positions[0]
        print(f"position: {pos.instrument} qty={pos.qty} avg={pos.avg_price}")
    else:
        print("position: (flat)")
    print(f"cash={engine.account.cash} daily_pnl={engine.account.daily_pnl}")


if __name__ == "__main__":
    main()
