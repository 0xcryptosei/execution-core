from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Event(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str
    instrument: str
    ts: datetime
    payload: dict[str, Any] = Field(default_factory=dict)
