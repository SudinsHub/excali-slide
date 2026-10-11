from collections.abc import Callable
from typing import Any

from app.jobs.context import JobContext

HANDLERS: dict[str, Callable[[JobContext], Any]] = {}


def handler(kind: str):
    """Decorator to register a job handler for a specific kind."""

    def decorator(fn: Callable[[JobContext], Any]):
        HANDLERS[kind] = fn
        return fn

    return decorator
