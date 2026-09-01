from decimal import Decimal

from execution_core.types import Account, Fill, Position, Side


def empty_position(instrument: str) -> Position:
    return Position(
        instrument=instrument,
        qty=Decimal("0"),
        avg_price=Decimal("0"),
        realized_pnl=Decimal("0"),
    )


def apply_fill(position: Position, fill: Fill, side: Side) -> Position:
    if side is not fill.side:
        msg = "fill side must match order side"
        raise ValueError(msg)

    qty = position.qty
    avg_price = position.avg_price
    realized_pnl = position.realized_pnl
    delta = fill.qty if side is Side.BUY else -fill.qty

    if qty == 0:
        return Position(
            instrument=position.instrument,
            qty=delta,
            avg_price=fill.price if delta != 0 else Decimal("0"),
            realized_pnl=realized_pnl,
        )

    if (qty > 0 and delta > 0) or (qty < 0 and delta < 0):
        new_qty = qty + delta
        new_avg = (
            (abs(qty) * avg_price) + (abs(delta) * fill.price)
        ) / abs(new_qty)
        return Position(
            instrument=position.instrument,
            qty=new_qty,
            avg_price=new_avg,
            realized_pnl=realized_pnl,
        )

    closed = min(abs(qty), abs(delta))
    if qty > 0:
        realized_pnl += closed * (fill.price - avg_price)
    else:
        realized_pnl += closed * (avg_price - fill.price)

    new_qty = qty + delta
    if new_qty == 0:
        new_avg = Decimal("0")
    elif (qty > 0 and new_qty > 0) or (qty < 0 and new_qty < 0):
        new_avg = avg_price
    else:
        new_avg = fill.price

    return Position(
        instrument=position.instrument,
        qty=new_qty,
        avg_price=new_avg,
        realized_pnl=realized_pnl,
    )


def apply_fill_to_account(account: Account, fill: Fill, side: Side) -> Account:
    before = next(
        (p for p in account.positions if p.instrument == fill.instrument),
        empty_position(fill.instrument),
    )
    after = apply_fill(before, fill, side)
    realized_delta = after.realized_pnl - before.realized_pnl

    if side is Side.BUY:
        cash = account.cash - (fill.qty * fill.price)
    else:
        cash = account.cash + (fill.qty * fill.price)

    positions = [p for p in account.positions if p.instrument != fill.instrument]
    if after.qty != 0:
        positions.append(after)

    return Account(
        account_id=account.account_id,
        cash=cash,
        daily_pnl=account.daily_pnl + realized_delta,
        positions=positions,
    )
