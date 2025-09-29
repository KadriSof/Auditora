"""
File: "src/auditora/adats/session.py"
Context: Bifrost - Context manager for clean setup and teardown of context objects.

Trivia: In Norse Mythology, 'Bifrost' is the bridge that connects Midgard with Asgard.
"""
from contextlib import contextmanager
from typing import Any

from .paragon import Paragon


_Paragon = Paragon()


@contextmanager
def bifrost(session: Any, monitor: Any, report: Any):
    """Context manager that activates context objects."""
    _Paragon.set_context(session=session, monitor=monitor, report=report)
    try:
        yield
    finally:
        _Paragon.clear_context()
