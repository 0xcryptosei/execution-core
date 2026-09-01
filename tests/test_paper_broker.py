from datetime import datetime, timezone
from decimal import Decimal

from execution_core.clock import FakeClock, SystemClock
from execution_core.paper_broker import PaperBroker
from execution_core.types import (
    Order,
    OrderPlan,
    OrderStatus,
    OrderType,
    RiskDecision,
    Side,
)


def _plan(
    *,
    client_id: str = "cli-1",
    qty: str = "1",
    order_type: OrderType = OrderType.MARKET,
    limit_price: str | None = None,
) -> OrderPlan:
    return OrderPlan(
        client_id=client_id,
        instrument="BTC-USD",
        side=Side.BUY,
        order_type=order_type,
        qty=Decimal(qty),
        limit_price=Decimal(limit_price) if limit_price else None,
        risk_decision=RiskDecision.ALLOW,
        reason="approved",
    )


def test_immediate_market_order_fills_at_last_price() -> None:
    broker = PaperBroker(last_price=Decimal("50000"))
    order = broker.place(_plan())

    assert order.status is OrderStatus.FILLED
    assert order.filled_qty == Decimal("1")
    assert broker.get_fills()[0].price == Decimal("50000")
    assert broker.get_open_orders() == []


def test_immediate_limit_order_fills_at_limit_price() -> None:
    broker = PaperBroker(last_price=Decimal("50000"))
    order = broker.place(_plan(order_type=OrderType.LIMIT, limit_price="49000"))

    assert order.status is OrderStatus.FILLED
    assert broker.get_fills()[0].price == Decimal("49000")


def test_duplicate_live_client_id_is_rejected() -> None:
    broker = PaperBroker(last_price=Decimal("50000"))
    live = Order(
        order_id="ord-live",
        client_id="cli-1",
        instrument="BTC-USD",
        side=Side.BUY,
        order_type=OrderType.MARKET,
        qty=Decimal("1"),
        status=OrderStatus.OPEN,
    )
    broker._orders[live.order_id] = live

    order = broker.place(_plan(client_id="cli-1"))

    assert order.status is OrderStatus.REJECTED
    assert broker.get_open_orders() == [live]


def test_cancel_open_order() -> None:
    broker = PaperBroker(last_price=Decimal("50000"))
    open_order = Order(
        order_id="ord-open",
        client_id="cli-9",
        instrument="BTC-USD",
        side=Side.BUY,
        order_type=OrderType.MARKET,
        qty=Decimal("1"),
        status=OrderStatus.OPEN,
    )
    broker._orders[open_order.order_id] = open_order

    cancelled = broker.cancel("ord-open")

    assert cancelled.status is OrderStatus.CANCELLED
    assert broker.get_open_orders() == []


def test_fake_clock_can_be_injected() -> None:
    moment = datetime(2026, 1, 1, tzinfo=timezone.utc)
    clock = FakeClock(moment)
    broker = PaperBroker(last_price=Decimal("1"), clock=clock)

    assert broker._clock.now() == moment
    assert isinstance(SystemClock().now(), datetime)
