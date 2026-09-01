from decimal import Decimal

from execution_core.position import apply_fill, apply_fill_to_account, empty_position
from execution_core.types import Account, Fill, Position, Side


def _fill(qty: str, price: str, *, side: Side = Side.BUY) -> Fill:
    return Fill(
        fill_id="fill-1",
        order_id="ord-1",
        instrument="BTC-USD",
        side=side,
        qty=Decimal(qty),
        price=Decimal(price),
    )


def test_apply_fill_opens_long_position() -> None:
    position = apply_fill(
        empty_position("BTC-USD"),
        _fill("2", "100"),
        Side.BUY,
    )

    assert position.qty == Decimal("2")
    assert position.avg_price == Decimal("100")
    assert position.realized_pnl == Decimal("0")


def test_apply_fill_realizes_pnl_on_close() -> None:
    open_position = apply_fill(
        empty_position("BTC-USD"),
        _fill("2", "100"),
        Side.BUY,
    )
    closed = apply_fill(
        open_position,
        _fill("2", "110", side=Side.SELL),
        Side.SELL,
    )

    assert closed.qty == Decimal("0")
    assert closed.realized_pnl == Decimal("20")


def test_apply_fill_to_account_updates_cash_and_daily_pnl() -> None:
    account = Account(account_id="acct-1", cash=Decimal("1000"))
    fill = _fill("1", "100")

    updated = apply_fill_to_account(account, fill, Side.BUY)

    assert updated.cash == Decimal("900")
    assert updated.daily_pnl == Decimal("0")
    assert updated.positions[0].qty == Decimal("1")

    sell_fill = _fill("1", "120", side=Side.SELL)
    updated = apply_fill_to_account(updated, sell_fill, Side.SELL)

    assert updated.cash == Decimal("1020")
    assert updated.daily_pnl == Decimal("20")
    assert updated.positions == []
