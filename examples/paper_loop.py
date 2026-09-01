#!/usr/bin/env python3
"""Minimal paper-trading loop demonstrating the execution-core pipeline."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal

from execution_core import FakeClock, KillSwitch, PaperBroker, RiskLimits, check
from execution_core.clock import SystemClock
from execution_core.engine import EngineContext, OrderStore
from execution_core.events import Event
from execution_core.position import apply_fill_to_account
from execution_core.types import Account, Intent, OrderStatus, OrderType, Position, RiskDecision, Side


class OneBuyStrategy:
    """Emit a single market BUY, then stop."""

    def __init__(self) -> None:
        self._done = False

    def propose(self, event: Event, ctx: EngineContext) -> Intent | None:
        del ctx
        if self._done:
            return None
        self._done = True
        return Intent(
            client_id="paper-demo-1",
            instrument=event.instrument,
            side=Side.BUY,
            order_type=OrderType.MARKET,
            qty=Decimal("1"),
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a paper-trading demo loop.")
    parser.add_argument(
        "--fake-clock",
        action="store_true",
        help="Use FakeClock instead of SystemClock.",
    )
    args = parser.parse_args()

    if args.fake_clock:
        clock = FakeClock(datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc))
        print(f"clock: FakeClock ({clock.now().isoformat()})")
    else:
        clock = SystemClock()
        print(f"clock: SystemClock ({clock.now().isoformat()})")

    account = Account(account_id="demo", cash=Decimal("10000"))
    positions: list[Position] = []
    limits = RiskLimits(max_order_qty=Decimal("10"), max_daily_loss=Decimal("5000"))
    kill_switch = KillSwitch()
    broker = PaperBroker(last_price=Decimal("50000"), clock=clock)
    store = OrderStore()
    strategy = OneBuyStrategy()

    events = [
        Event(type="tick", instrument="BTC-USD", ts=clock.now()),
        Event(type="tick", instrument="BTC-USD", ts=clock.now()),
    ]

    for index, event in enumerate(events, start=1):
        print(f"\n--- event {index} ({event.type}) ---")

        if kill_switch.halted:
            print(f"halted: {kill_switch.reason}")
            break

        ctx = EngineContext(
            account=account,
            positions=positions,
            halted=kill_switch.halted,
        )
        intent = strategy.propose(event, ctx)
        if intent is None:
            print("intent: (none)")
            continue

        plan = check(intent, account, positions, 0, clock.now(), limits)
        print(
            f"plan: {plan.risk_decision.value} — {plan.reason} (qty={plan.qty})"
        )

        if plan.risk_decision is RiskDecision.REJECT:
            continue
        if store.has_live_order(intent.client_id):
            print("skipped: duplicate client_id")
            continue

        fills_before = len(broker.get_fills())
        order = broker.place(plan)
        if order.status is OrderStatus.REJECTED:
            print("order: REJECTED")
            continue

        store.register(order.client_id)
        new_fills = broker.get_fills()[fills_before:]
        for fill in new_fills:
            print(f"fill: {fill.side.value} {fill.qty} @ {fill.price}")
            account = apply_fill_to_account(account, fill, fill.side)
        positions = list(account.positions)

        if (
            limits.max_daily_loss is not None
            and account.daily_pnl <= -limits.max_daily_loss
        ):
            kill_switch.halt("daily_loss")

    print("\n--- final ---")
    if positions:
        position = positions[0]
        print(
            f"position: {position.instrument} "
            f"qty={position.qty} avg_price={position.avg_price}"
        )
    else:
        print("position: (flat)")
    print(f"cash={account.cash} daily_pnl={account.daily_pnl}")


if __name__ == "__main__":
    main()
