from decimal import Decimal

from execution_core import (
    Account,
    Fill,
    Intent,
    Order,
    OrderStatus,
    OrderType,
    Position,
    RiskDecision,
    Side,
)


def test_intent_market_order_construction() -> None:
    intent = Intent(
        client_id="cli-1",
        instrument="BTC-USD",
        side=Side.BUY,
        order_type=OrderType.MARKET,
        qty=Decimal("1.5"),
    )

    assert intent.client_id == "cli-1"
    assert intent.instrument == "BTC-USD"
    assert intent.limit_price is None
    assert intent.qty == Decimal("1.5")


def test_intent_limit_order_with_decimal_price() -> None:
    intent = Intent(
        client_id="cli-2",
        instrument="ETH-USD",
        side=Side.SELL,
        order_type=OrderType.LIMIT,
        qty=Decimal("10"),
        limit_price=Decimal("2500.50"),
    )

    assert intent.order_type is OrderType.LIMIT
    assert intent.limit_price == Decimal("2500.50")


def test_order_fill_and_account_construction() -> None:
    order = Order(
        order_id="ord-1",
        client_id="cli-1",
        instrument="BTC-USD",
        side=Side.BUY,
        order_type=OrderType.LIMIT,
        qty=Decimal("2"),
        limit_price=Decimal("50000"),
        status=OrderStatus.OPEN,
    )
    fill = Fill(
        fill_id="fill-1",
        order_id="ord-1",
        instrument="BTC-USD",
        side=Side.BUY,
        qty=Decimal("2"),
        price=Decimal("49999.50"),
    )
    account = Account(
        account_id="acct-1",
        cash=Decimal("100000"),
        positions=[
            Position(
                instrument="BTC-USD",
                qty=Decimal("2"),
                avg_price=Decimal("49999.50"),
            )
        ],
    )

    assert order.status is OrderStatus.OPEN
    assert fill.price == Decimal("49999.50")
    assert account.positions[0].qty == Decimal("2")
    assert RiskDecision.ALLOW.value == "ALLOW"
