from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict

_STRICT = ConfigDict(extra="forbid")


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    OPEN = "OPEN"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class RiskDecision(str, Enum):
    ALLOW = "ALLOW"
    RESIZE = "RESIZE"
    REJECT = "REJECT"


class Intent(BaseModel):
    model_config = _STRICT

    client_id: str
    instrument: str
    side: Side
    order_type: OrderType
    qty: Decimal
    limit_price: Optional[Decimal] = None


class OrderPlan(BaseModel):
    model_config = _STRICT

    client_id: str
    instrument: str
    side: Side
    order_type: OrderType
    qty: Decimal
    limit_price: Optional[Decimal] = None
    risk_decision: RiskDecision
    reason: str


class Order(BaseModel):
    model_config = _STRICT

    order_id: str
    client_id: str
    instrument: str
    side: Side
    order_type: OrderType
    qty: Decimal
    status: OrderStatus
    limit_price: Optional[Decimal] = None
    filled_qty: Decimal = Decimal("0")


class Fill(BaseModel):
    model_config = _STRICT

    fill_id: str
    order_id: str
    instrument: str
    side: Side
    qty: Decimal
    price: Decimal


class Position(BaseModel):
    model_config = _STRICT

    instrument: str
    qty: Decimal
    avg_price: Decimal


class Account(BaseModel):
    model_config = _STRICT

    account_id: str
    cash: Decimal
    daily_pnl: Decimal = Decimal("0")
    positions: list[Position] = []


class RiskLimits(BaseModel):
    model_config = _STRICT

    max_order_qty: Optional[Decimal] = None
    max_position_qty: Optional[Decimal] = None
    max_order_notional: Optional[Decimal] = None
    max_daily_loss: Optional[Decimal] = None
    max_orders_per_minute: Optional[int] = None
