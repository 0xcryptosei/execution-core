from datetime import datetime, timezone
from decimal import Decimal

from execution_core import (
    Account,
    Intent,
    OrderType,
    Position,
    RiskDecision,
    RiskLimits,
    Side,
)
from execution_core.risk import check


def _intent(qty: str, *, limit_price: str | None = None) -> Intent:
    return Intent(
        client_id="cli-1",
        instrument="BTC-USD",
        side=Side.BUY,
        order_type=OrderType.LIMIT if limit_price else OrderType.MARKET,
        qty=Decimal(qty),
        limit_price=Decimal(limit_price) if limit_price else None,
    )


def _account(*, daily_pnl: str = "0") -> Account:
    return Account(
        account_id="acct-1",
        cash=Decimal("100000"),
        daily_pnl=Decimal(daily_pnl),
    )


def _limits(**kwargs: object) -> RiskLimits:
    return RiskLimits(**kwargs)


def _check(
    intent: Intent,
    account: Account,
    positions: list[Position],
    limits: RiskLimits,
    *,
    open_order_count_window: int = 0,
) -> object:
    return check(
        intent,
        account,
        positions,
        open_order_count_window,
        datetime.now(timezone.utc),
        limits,
    )


def test_zero_qty_reject() -> None:
    plan = _check(
        _intent("0"),
        _account(),
        [],
        _limits(max_order_qty=Decimal("10")),
    )

    assert plan.risk_decision is RiskDecision.REJECT
    assert plan.reason == "quantity must be positive"


def test_oversized_order_resized_to_max_order_qty() -> None:
    plan = _check(
        _intent("100", limit_price="50000"),
        _account(),
        [],
        _limits(max_order_qty=Decimal("10")),
    )

    assert plan.risk_decision is RiskDecision.RESIZE
    assert plan.qty == Decimal("10")
    assert "max_order_qty" in plan.reason


def test_oversized_notional_rejected() -> None:
    plan = _check(
        _intent("2", limit_price="50000"),
        _account(),
        [],
        _limits(max_order_notional=Decimal("50000")),
    )

    assert plan.risk_decision is RiskDecision.REJECT
    assert "max_order_notional" in plan.reason


def test_position_cap_resizes_qty() -> None:
    positions = [
        Position(
            instrument="BTC-USD",
            qty=Decimal("8"),
            avg_price=Decimal("50000"),
        )
    ]
    plan = _check(
        _intent("5"),
        _account(),
        positions,
        _limits(max_position_qty=Decimal("10")),
    )

    assert plan.risk_decision is RiskDecision.RESIZE
    assert plan.qty == Decimal("2")
    assert "max_position_qty" in plan.reason


def test_daily_loss_reject() -> None:
    plan = _check(
        _intent("1", limit_price="50000"),
        _account(daily_pnl="-6000"),
        [],
        _limits(max_daily_loss=Decimal("5000")),
    )

    assert plan.risk_decision is RiskDecision.REJECT
    assert plan.reason == "daily loss limit exceeded"
