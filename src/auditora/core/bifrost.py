"""
File: "src/auditora/adats/session.py"
Context: Bifrost - Context manager for clean setup and teardown of context objects.

Trivia: In Norse Mythology, 'Bifrost' is the bridge that connects Midgard with Asgard.
"""
from contextlib import contextmanager, asynccontextmanager
from typing import Any

from .paragon import _PARAGON


@contextmanager
def bifrost_sync(session: Any, monitor: Any, report: Any):
    """Sync context manager version of bifrost."""
    token = _PARAGON.set_context(session=session, monitor=monitor, report=report)
    try:
        yield
    finally:
        _PARAGON.reset_context(token=token)


@asynccontextmanager
async def bifrost_async(session: Any, monitor: Any, report: Any):
    """Async context manager version of bifrost."""
    token = _PARAGON.set_context(session=session, monitor=monitor, report=report)
    try:
        yield
    finally:
        _PARAGON.reset_context(token=token)
