import logging
from logging import basicConfig


def configure_logging(level: str = "INFO") -> None:
    """Configure root logging for execution-core consumers."""
    basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
