"""
Paragon - Thread-local context storage manager for Auditora.
"""
import threading
from typing import Any, Dict


class Paragon:
    """Thread-local storage manager for all context objects (Adats)."""
    def __init__(self):
        self._local = threading.local()

    def set_context(self, session: Any, monitor: Any, report: Any) -> None:
        """
        Set all context objects (Adats) for current thread.

        Args:
            session (Any): Session object (Adat) for session related data.
            monitor (Any): Monitor object (Adat) for monitor related data.
            report (Any): Report object (Adat) for report related data.
        """
        self._local.context = {
            'session': session,
            'monitor': monitor,
            'report': report,
        }

    def get_context(self) -> Dict[str, Any]:
        """
        Get current context objects (Adats) for current thread.
        """
        if not hasattr(self._local, 'context'):
            raise RuntimeError(
                "[Paragon] Context not active. Use the context wrapper decorator,"
                "or manually active the context with bifrost context manager."
            )
        return self._local.context

    def clear_context(self) -> None:
        """Clear current context objects (Adats) for current thread."""
        if hasattr(self._local, 'context'):
            del self._local.context