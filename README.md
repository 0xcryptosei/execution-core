# execution-core

execution-core is a venue-agnostic paper execution library for simulating order placement and fills without connecting to live markets. It is designed as a reusable foundation for backtests, strategy development, and integration testing. The API and execution model are intentionally minimal at this stage.

**Status:** scaffold only — not usable yet.

**What is NOT included:** API keys, venue SDKs, or trading signals.

## Install

```bash
python -m venv venv
venv\Scripts\activate
pip install -e ".[dev]"
```

On macOS or Linux, activate with `source venv/bin/activate` instead.
