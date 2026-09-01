from decimal import Decimal
from enum import Enum
from itertools import count
from typing import Optional

from execution_core.clock import Clock, SystemClock
from execution_core.types import Fill, Order, OrderPlan, OrderStatus, OrderType, RiskDecision


class FillMode(str, Enum):
    IMMEDIATE = "IMMEDIATE"


_LIVE_STATUSES = {
    OrderStatus.PENDING,
    OrderStatus.OPEN,
    OrderStatus.PARTIALLY_FILLED,
}


class PaperBroker:
    """Paper broker with immediate fills.

    Duplicate ``client_id``: if a live order (``PENDING``, ``OPEN``, or
    ``PARTIALLY_FILLED``) already exists for the same ``client_id``, ``place``
    returns an ``Order`` with status ``REJECTED`` instead of raising.
    """

    def __init__(
        self,
        last_price: Decimal,
        *,
        clock: Optional[Clock] = None,
        fill_mode: FillMode = FillMode.IMMEDIATE,
    ) -> None:
        self._clock = clock or SystemClock()
        self._last_price = last_price
        self._fill_mode = fill_mode
        self._orders: dict[str, Order] = {}
        self._fills: list[Fill] = []
        self._order_id_counter = count(1)
        self._fill_id_counter = count(1)

    def place(self, plan: OrderPlan) -> Order:
        if plan.risk_decision is RiskDecision.REJECT:
            return self._make_order(plan, OrderStatus.REJECTED)

        if self._has_live_client_order(plan.client_id):
            return self._make_order(plan, OrderStatus.REJECTED)

        order = self._make_order(plan, OrderStatus.OPEN)
        self._orders[order.order_id] = order

        if self._fill_mode is FillMode.IMMEDIATE:
            fill_price = self._fill_price(plan)
            order = Order(
                order_id=order.order_id,
                client_id=order.client_id,
                instrument=order.instrument,
                side=order.side,
                order_type=order.order_type,
                qty=order.qty,
                status=OrderStatus.FILLED,
                limit_price=order.limit_price,
                filled_qty=order.qty,
            )
            self._orders[order.order_id] = order
            self._record_fill(order, fill_price)

        return order

    def cancel(self, order_id: str) -> Order:
        order = self._orders.get(order_id)
        if order is None:
            msg = f"unknown order_id: {order_id}"
            raise KeyError(msg)
        if order.status not in _LIVE_STATUSES:
            msg = f"order {order_id} is not cancellable"
            raise ValueError(msg)

        cancelled = Order(
            order_id=order.order_id,
            client_id=order.client_id,
            instrument=order.instrument,
            side=order.side,
            order_type=order.order_type,
            qty=order.qty,
            status=OrderStatus.CANCELLED,
            limit_price=order.limit_price,
            filled_qty=order.filled_qty,
        )
        self._orders[order_id] = cancelled
        return cancelled

    def get_open_orders(self) -> list[Order]:
        return [
            order
            for order in self._orders.values()
            if order.status in _LIVE_STATUSES
        ]

    def get_fills(self) -> list[Fill]:
        return list(self._fills)

    def _has_live_client_order(self, client_id: str) -> bool:
        return any(
            order.client_id == client_id and order.status in _LIVE_STATUSES
            for order in self._orders.values()
        )

    def _fill_price(self, plan: OrderPlan) -> Decimal:
        if plan.order_type is OrderType.LIMIT:
            if plan.limit_price is None:
                msg = "limit order requires limit_price"
                raise ValueError(msg)
            return plan.limit_price
        return self._last_price

    def _make_order(self, plan: OrderPlan, status: OrderStatus) -> Order:
        order_id = f"ord-{next(self._order_id_counter)}"
        return Order(
            order_id=order_id,
            client_id=plan.client_id,
            instrument=plan.instrument,
            side=plan.side,
            order_type=plan.order_type,
            qty=plan.qty,
            status=status,
            limit_price=plan.limit_price,
            filled_qty=Decimal("0"),
        )

    def _record_fill(self, order: Order, price: Decimal) -> None:
        fill = Fill(
            fill_id=f"fill-{next(self._fill_id_counter)}",
            order_id=order.order_id,
            instrument=order.instrument,
            side=order.side,
            qty=order.qty,
            price=price,
        )
        self._fills.append(fill)
