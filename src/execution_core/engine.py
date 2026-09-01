import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Protocol

from execution_core.clock import Clock
from execution_core.events import Event
from execution_core.position import apply_fill_to_account
from execution_core.protocols import Broker
from execution_core.risk import check
from execution_core.types import (
    Account,
    Fill,
    Intent,
    OrderStatus,
    Position,
    RiskDecision,
    RiskLimits,
)

logger = logging.getLogger(__name__)


@dataclass
class EngineContext:
    account: Account
    positions: list[Position]
    halted: bool


class Strategy(Protocol):
    def propose(self, event: Event, ctx: EngineContext) -> Intent | None: ...


class KillSwitch:
    def __init__(self) -> None:
        self._halted = False
        self.reason: str | None = None

    @property
    def halted(self) -> bool:
        return self._halted

    def halt(self, reason: str) -> None:
        self._halted = True
        self.reason = reason
        logger.warning("kill switch engaged: %s", reason)


class OrderStore:
    def __init__(self) -> None:
        self._client_ids: set[str] = set()

    def has_live_order(self, client_id: str) -> bool:
        return client_id in self._client_ids

    def register(self, client_id: str) -> None:
        self._client_ids.add(client_id)


class Engine:
    def __init__(
        self,
        risk_limits: RiskLimits,
        kill_switch: KillSwitch,
        broker: Broker,
        strategy: Strategy,
        clock: Clock,
        *,
        account: Optional[Account] = None,
    ) -> None:
        self._risk_limits = risk_limits
        self._kill_switch = kill_switch
        self._broker = broker
        self._strategy = strategy
        self._clock = clock
        self._account = account or Account(
            account_id="paper",
            cash=Decimal("1000000"),
        )
        self._positions = list(self._account.positions)
        self._store = OrderStore()
        self._order_times: list[datetime] = []

    @property
    def account(self) -> Account:
        return self._account

    @property
    def positions(self) -> list[Position]:
        return list(self._positions)

    @property
    def halted(self) -> bool:
        return self._kill_switch.halted

    @property
    def halt_reason(self) -> str | None:
        return self._kill_switch.reason

    def halt(self, reason: str) -> None:
        self._kill_switch.halt(reason)
        self._cancel_open_orders()

    def on_event(self, event: Event) -> list[Fill]:
        if self._kill_switch.halted:
            logger.debug("event skipped: engine halted")
            self._cancel_open_orders()
            return []

        ctx = EngineContext(
            account=self._account,
            positions=self._positions,
            halted=self._kill_switch.halted,
        )
        intent = self._strategy.propose(event, ctx)
        if intent is None:
            return []

        if self._store.has_live_order(intent.client_id):
            logger.debug(
                "event skipped: duplicate client_id=%s", intent.client_id
            )
            return []

        plan = check(
            intent,
            self._account,
            self._positions,
            self._open_order_count_window(),
            self._clock.now(),
            self._risk_limits,
        )
        if plan.risk_decision is RiskDecision.REJECT:
            return []

        fills_before = len(self._broker.get_fills())
        order = self._broker.place(plan)
        if order.status is OrderStatus.REJECTED:
            logger.warning(
                "broker rejected order client_id=%s", intent.client_id
            )
            return []

        self._store.register(order.client_id)
        self._order_times.append(self._clock.now())

        new_fills = self._broker.get_fills()[fills_before:]
        for fill in new_fills:
            self._account = apply_fill_to_account(self._account, fill, fill.side)
        self._positions = list(self._account.positions)

        if new_fills:
            logger.info(
                "event processed instrument=%s fills=%d daily_pnl=%s",
                event.instrument,
                len(new_fills),
                self._account.daily_pnl,
            )

        if (
            self._risk_limits.max_daily_loss is not None
            and self._account.daily_pnl <= -self._risk_limits.max_daily_loss
        ):
            self._kill_switch.halt("daily_loss")
            self._cancel_open_orders()

        return new_fills

    def _open_order_count_window(self) -> int:
        now = self._clock.now()
        cutoff = now - timedelta(minutes=1)
        self._order_times = [ts for ts in self._order_times if ts >= cutoff]
        return len(self._order_times)

    def _cancel_open_orders(self) -> None:
        for order in self._broker.get_open_orders():
            self._broker.cancel(order.order_id)
