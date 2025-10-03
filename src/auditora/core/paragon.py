"""
File: "src/auditora/core/paragon.py"
Context: Paragon - Thread-local context storage manager for Auditora.
"""
import contextvars
from typing import Any, Dict


class Paragon:
    """Thread-local storage manager for all context objects (Adats)."""
    def __init__(self):
        # One contextvar holding a dict of {session, monitor, report}
        self._context: contextvars.ContextVar[Dict[str, Any] | None] = (
            contextvars.ContextVar("auditora_context", default=None)
        )

    def set_context(self, session: Any, monitor: Any, report: Any) -> contextvars.Token:
        """
        Set all context objects (Adats) for current thread.

        Args:
            session (Any): Session object (Adat) for session related data.
            monitor (Any): Monitor object (Adat) for monitor related data.
            report (Any): Report object (Adat) for report related data.

        Returns:
            Token: A Token object will be used to safely restore the context to its previous state.
        """
        return self._context.set(
            {
                'session': session,
                'monitor': monitor,
                'report': report,
            }
        )

    def get_context(self) -> Dict[str, Any]:
        """
        Get current context objects (Adats) for current thread.

        Returns:
            Dict[str, Any]: Current context objects (Adats) for current thread.

        Raises:
            RuntimeError: If context is not active.
        """
        context = self._context.get()
        if context is None:
            raise RuntimeError(
                "[Paragon] Context not active. Use the context wrapper decorator "
                "or manually activate the context with the bifrost context manager."
            )
        return context

    @staticmethod
    def copy_current_context() -> contextvars.Context:
        """
        Copy the entire current execution context for propagation.
        (For future thread pools and async task spawning context propagation use cases)

        Returns:
            Context: Complete copy of the current execution context.
        """
        return contextvars.copy_context()

    def reset_context(self, token: contextvars.Token) -> None:
        """Reset current context object to its previous state using token."""
        self._context.reset(token)


_PARAGON = Paragon()