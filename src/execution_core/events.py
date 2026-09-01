from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Event(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str
    instrument: str
    ts: datetime
    payload: dict[str, Any] = Field(default_factory=dict)


def tick_event(
    instrument: str,
    *,
    ts: datetime | None = None,
    **payload: Any,
) -> Event:
    return Event(
        type="tick",
        instrument=instrument,
        ts=ts or datetime.now(timezone.utc),
        payload=dict(payload),
    )


def bar_event(
    instrument: str,
    *,
    ts: datetime | None = None,
    **payload: Any,
) -> Event:
    return Event(
        type="bar",
        instrument=instrument,
        ts=ts or datetime.now(timezone.utc),
        payload=dict(payload),
    )
