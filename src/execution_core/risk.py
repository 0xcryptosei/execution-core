import logging
from datetime import datetime
from decimal import Decimal

from execution_core.types import (
    Account,
    Intent,
    OrderPlan,
    Position,
    RiskDecision,
    RiskLimits,
    Side,
)

logger = logging.getLogger(__name__)


def _position_qty(positions: list[Position], instrument: str) -> Decimal:
    for position in positions:
        if position.instrument == instrument:
            return position.qty
    return Decimal("0")


def _price_for_notional(intent: Intent) -> Decimal:
    if intent.limit_price is not None:
        return intent.limit_price
    return Decimal("0")


def _max_qty_for_position_cap(
    current: Decimal, side: Side, max_position_qty: Decimal
) -> Decimal:
    if side is Side.BUY:
        max_qty = max_position_qty - current
        min_qty = -max_position_qty - current
    else:
        max_qty = current + max_position_qty
        min_qty = current - max_position_qty

    if max_qty <= 0 or min_qty > max_qty:
        return Decimal("0")
    return max_qty


def _reject_plan(intent: Intent, reason: str) -> OrderPlan:
    logger.info(
        "risk reject client_id=%s instrument=%s reason=%s",
        intent.client_id,
        intent.instrument,
        reason,
    )
    return OrderPlan(
        client_id=intent.client_id,
        instrument=intent.instrument,
        side=intent.side,
        order_type=intent.order_type,
        qty=intent.qty,
        limit_price=intent.limit_price,
        risk_decision=RiskDecision.REJECT,
        reason=reason,
    )


def _allow_or_resize_plan(intent: Intent, qty: Decimal, reason: str) -> OrderPlan:
    if qty < intent.qty:
        decision = RiskDecision.RESIZE
        logger.info(
            "risk resize client_id=%s instrument=%s qty=%s reason=%s",
            intent.client_id,
            intent.instrument,
            qty,
            reason,
        )
    else:
        decision = RiskDecision.ALLOW
        logger.debug(
            "risk allow client_id=%s instrument=%s qty=%s",
            intent.client_id,
            intent.instrument,
            qty,
        )

    return OrderPlan(
        client_id=intent.client_id,
        instrument=intent.instrument,
        side=intent.side,
        order_type=intent.order_type,
        qty=qty,
        limit_price=intent.limit_price,
        risk_decision=decision,
        reason=reason,
    )


def check(
    intent: Intent,
    account: Account,
    positions: list[Position],
    open_order_count_window: int,
    _now: datetime,
    limits: RiskLimits,
) -> OrderPlan:
    if intent.qty <= 0:
        return _reject_plan(intent, "quantity must be positive")

    if (
        limits.max_daily_loss is not None
        and account.daily_pnl <= -limits.max_daily_loss
    ):
        return _reject_plan(intent, "daily loss limit exceeded")

    if (
        limits.max_orders_per_minute is not None
        and open_order_count_window >= limits.max_orders_per_minute
    ):
        return _reject_plan(intent, "order rate limit exceeded")

    qty = intent.qty
    reasons: list[str] = []

    if limits.max_order_qty is not None and qty > limits.max_order_qty:
        qty = limits.max_order_qty
        reasons.append(f"resized to max_order_qty {limits.max_order_qty}")

    if limits.max_position_qty is not None:
        current = _position_qty(positions, intent.instrument)
        cap_qty = _max_qty_for_position_cap(
            current, intent.side, limits.max_position_qty
        )
        if qty > cap_qty:
            qty = cap_qty
            reasons.append(
                f"resized to stay within max_position_qty {limits.max_position_qty}"
            )

    if qty <= 0:
        return _reject_plan(intent, "position limit leaves no executable quantity")

    if limits.max_order_notional is not None:
        notional = qty * _price_for_notional(intent)
        if notional > limits.max_order_notional:
            return _reject_plan(
                intent,
                f"notional {notional} exceeds max_order_notional "
                f"{limits.max_order_notional}",
            )

    if qty < intent.qty:
        reason = "; ".join(reasons) if reasons else "quantity reduced by risk limits"
        return _allow_or_resize_plan(intent, qty, reason)

    return _allow_or_resize_plan(intent, qty, "approved")
