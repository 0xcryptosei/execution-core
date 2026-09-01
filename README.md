# execution-core

Venue-agnostic paper execution for strategies: events in, risk-checked orders and fills out—no live venue required.

## Status

Paper-trading library with types, risk checks, a paper broker, position accounting, and an event-driven engine. Suitable for backtests, integration tests, and product repos that wrap live adapters around this core.

## Contains

- Pydantic domain types (`Intent`, `Order`, `Fill`, `Position`, `Account`, …)
- Pre-trade risk (`check`) with resize / reject decisions
- `PaperBroker` with immediate fill mode
- Signed position and PnL accounting
- `Engine` orchestrating strategy → risk → broker → state
- `KillSwitch`, idempotent `client_id` tracking, injectable clocks

## Does not contain

- API keys or secrets handling beyond a sample `.env.example`
- Venue SDKs (Binance, IBKR, etc.)
- Signal generation or alpha research tooling
- Live order routing

Live venue adapters belong in **product repos** that depend on `execution-core` and implement broker protocols against real APIs.

## Install

```bash
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux
pip install -e ".[dev]"
```

## Verify

```bash
pytest -q
```

## Example

```bash
python examples/paper_loop.py
python examples/paper_loop.py --fake-clock
```

See [docs/architecture.md](docs/architecture.md) for the event pipeline, idempotency, and kill-switch behavior.

## Public API

| Module | Exports |
|--------|---------|
| `execution_core.types` | `Side`, `OrderType`, `OrderStatus`, `RiskDecision`, `Intent`, `OrderPlan`, `Order`, `Fill`, `Position`, `Account`, `RiskLimits` |
| `execution_core.events` | `Event` |
| `execution_core.risk` | `check` |
| `execution_core.position` | `apply_fill`, `apply_fill_to_account`, `empty_position` |
| `execution_core.paper_broker` | `PaperBroker`, `FillMode` |
| `execution_core.clock` | `Clock`, `SystemClock`, `FakeClock` |
| `execution_core.engine` | `Engine`, `EngineContext`, `Strategy`, `KillSwitch`, `OrderStore` |

Import from the package root:

```python
from execution_core import Engine, Event, PaperBroker, RiskLimits, check
```

Quantities and prices use `Decimal`. Models reject unknown fields (`extra="forbid"`).

## License

MIT — see [LICENSE](LICENSE).
