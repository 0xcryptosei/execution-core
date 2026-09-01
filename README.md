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
python examples/engine_demo.py --log-level INFO
```

See [docs/architecture.md](docs/architecture.md) for the event pipeline, idempotency, and kill-switch behavior.

## Public API

```python
from execution_core import (
    Engine,
    FakeClock,
    Intent,
    KillSwitch,
    OrderPlan,
    PaperBroker,
    RiskChecker,
    RiskLimits,
    check,
)
from execution_core.events import Event, bar_event, tick_event
from execution_core.logging_config import configure_logging
from execution_core.protocols import Broker
```

Additional types and helpers live in submodules (`execution_core.types`, `execution_core.engine`, …) for tests and product integrations.

Quantities and prices use `Decimal`. Models reject unknown fields (`extra="forbid"`).

## License

MIT — see [LICENSE](LICENSE).
