# execution-core

execution-core is a venue-agnostic paper execution library for simulating order placement and fills without connecting to live markets. It is designed as a reusable foundation for backtests, strategy development, and integration testing. The API and execution model are intentionally minimal at this stage.

**Status:** scaffold only — not usable yet.

**What is NOT included:** API keys, venue SDKs, or trading signals.

## Public types

- **Enums:** `Side`, `OrderType`, `OrderStatus`, `RiskDecision` (`ALLOW`, `RESIZE`, `REJECT`)
- **Requests / plans:** `Intent`, `OrderPlan`
- **Execution state:** `Order`, `Fill`, `Position`, `Account`
- **Configuration:** `RiskLimits`
- **Instrument:** string field on order-related models (e.g. `"BTC-USD"`)

Quantities and prices use `Decimal`. Models reject unknown fields.

## Install

```bash
python -m venv venv
venv\Scripts\activate
pip install -e ".[dev]"
```

On macOS or Linux, activate with `source venv/bin/activate` instead.
