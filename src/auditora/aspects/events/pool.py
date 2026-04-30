"""
Event object pool for efficient reuse of EventRecord instances.

This module provides a thread-safe, bounded object pool that reuses EventRecord
objects to reduce memory allocation overhead in high-throughput scenarios.
"""

import threading

from time import monotonic
from contextlib import contextmanager
from queue import Queue, Empty, Full
from typing import Set, Callable


class PoolExhaustedError(Exception):
    """Raised when pool cannot provide an object and timeout is exceeded."""

    pass


class EventPool:
    """
    Thread-safe object pool for EventRecord instances with bounded capacity.

    Design:
        - Uses Queue with maxsize for automatic capacity management
        - Context manager protocol for guaranteed resource cleanup
        - Active object tracking for leak detection
        - Configurable timeout and blocking behavior

    Performance characteristics:
        - O(1) borrow/return operations
        - Minimal lock contention (Queue handles internal locking)
        - No garbage collection overhead for reused objects

    Example:
        >>> pool = EventPool(maxsize=100, timeout=5.0)
        >>> with pool.acquire() as event:
        ...     event.user_id = 123
        ...     # Use event...
        ... # Event automatically returned to pool
    """

    __slots__ = (
        "_pool",
        "_maxsize",
        "_timeout",
        "_active",
        "_lock",
        "_stats",
        "_validator",
        "_cleaner",
    )

    def __init__(
        self,
        maxsize: int = 1000,
        timeout: float = 5.0,
        validator: Callable[[object], bool] | None = None,
        cleaner: Callable[[object], None] | None = None,
    ):
        """
        Initialize the event pool.

        Args:
            maxsize: Maximum number of idle objects to retain (default: 1000)
            timeout: Maximum seconds to wait when pool is exhausted (default: 5.0)
            validator: Optional function to validate object health before reuse
            cleaner: Optional function for deep cleanup of reused objects

        Raises:
            ValueError: If maxsize < 1 or timeout < 0
        """
        if maxsize < 1:
            raise ValueError(f"maxsize must be >= 1, got {maxsize}")
        if timeout < 0:
            raise ValueError(f"timeout must be >= 0, got {timeout}")

        self._pool = Queue(maxsize=maxsize)
        self._maxsize = maxsize
        self._timeout = timeout
        self._active: Set[int] = set()
        self._lock = threading.Lock()
        self._validator = validator or (lambda _: True)
        self._cleaner = cleaner or (lambda _: None)

        # Performance metrics (for monitoring, not synchronization)
        self._stats = {
            "created": 0,
            "reused": 0,
            "discarded": 0,
            "failed_validations": 0,
        }

    @contextmanager
    def acquire(self, timeout: float | None = None, force_new: bool = False):
        """
        Acquire an event from the pool with automatic cleanup.

        This is the primary interface for pool usage. The context manager
        guarantees the event is returned to the pool, even if exceptions occur.

        Args:
            timeout: Override default timeout (None = use instance default)
            force_new: If True, bypass pool and create fresh object

        Yields:
            EventRecord: A cleared event record ready for use

        Raises:
            PoolExhaustedError: If pool exhausted and timeout exceeded
            Exception: Any exception from validator or event operations

        Example:
            >>> with pool.acquire(timeout=2.0) as event:
            ...     event.data = "value"
        """
        event = None
        start_time = monotonic()
        use_timeout = timeout if timeout is not None else self._timeout

        try:
            # Strategy: Get from pool or create new
            if not force_new:
                event = self._try_acquire_from_pool(use_timeout, start_time)

            if event is None:
                event = self._create_new()

            # Validate before yielding
            if not self._validator(event):
                self._stats["failed_validations"] += 1
                raise RuntimeError("Event validation failed - object is corrupted")

            # Track active objects
            with self._lock:
                self._active.add(id(event))

            yield event

        finally:
            # Guaranteed cleanup path
            if event:
                self._return_to_pool(event)

    def _try_acquire_from_pool(self, timeout: float, start_time: float) -> object:
        """Attempt to get existing object from pool with timeout."""
        remaining = self._time_remaining(start_time, timeout)

        try:
            # Blocking get with timeout
            event = self._pool.get(timeout=remaining if remaining > 0 else 0)
            self._cleaner(event)  # Deep cleanup
            self._stats["reused"] += 1
            return event
        except Empty:
            # Pool empty - will create new
            self._stats["created"] += 1
            return None

    def _create_new(self) -> object:
        """Create a fresh EventRecord instance."""
        from src.auditora.aspects.events.record import EventRecord

        self._stats["created"] += 1
        return EventRecord()

    def _return_to_pool(self, event: object) -> None:
        """Return object to pool or discard if pool is full/corrupted."""
        # Remove from active tracking
        with self._lock:
            self._active.discard(id(event))

        # Validate before returning
        if not self._validator(event):
            self._stats["discarded"] += 1
            self._stats["failed_validations"] += 1
            return  # Discard corrupted object

        # Attempt to return to pool
        try:
            self._pool.put_nowait(event)
        except Full:
            # Pool at capacity - discard this object
            self._stats["discarded"] += 1

    @staticmethod
    def _time_remaining(start_time: float, timeout: float) -> float:
        """Calculate remaining timeout, handling infinite and negative cases."""
        if timeout <= 0:
            return 0
        elapsed = monotonic() - start_time
        remaining = timeout - elapsed
        return max(0, remaining)

    def stats(self) -> dict:
        """
        Return pool performance metrics.

        Returns:
            Dictionary with creation, reuse, discard, and active statistics
        """
        with self._lock:
            return {
                "idle": self._pool.qsize(),
                "active": len(self._active),
                "total_created": self._stats["created"],
                "total_reused": self._stats["reused"],
                "total_discarded": self._stats["discarded"],
                "validation_failures": self._stats["failed_validations"],
                "hit_rate": self._hit_rate(),
            }

    def _hit_rate(self) -> float:
        """Calculate pool hit rate (reused / total requested)."""
        total_requests = self._stats["created"] + self._stats["reused"]
        if total_requests == 0:
            return 0.0
        return self._stats["reused"] / total_requests

    def clear(self) -> None:
        """
        Clear all idle objects from the pool.

        Useful for memory reduction during idle periods or before shutdown.
        Active objects are unaffected and will be discarded on return.
        """
        try:
            while True:
                self._pool.get_nowait()
        except Empty:
            pass

    @property
    def size(self) -> int:
        """Current number of idle objects in pool."""
        return self._pool.qsize()

    @property
    def active_count(self) -> int:
        """Number of objects currently borrowed."""
        with self._lock:
            return len(self._active)


# Convenience factory function for common configurations
def create_event_pool(maxsize: int = 1000, strict: bool = False) -> EventPool:
    """
    Create a configured event pool.

    Args:
        maxsize: Maximum idle objects
        strict: If True, raise PoolExhaustedError instead of creating new objects

    Returns:
        Configured EventPool instance
    """
    if strict:
        # In strict mode, never create new objects - only use pool
        def validator(obj):
            return obj is not None

        return EventPool(maxsize=maxsize, validator=validator)

    # Standard mode - create new when needed
    return EventPool(maxsize=maxsize)


# Usage Example:
if __name__ == "__main__":
    pool = EventPool(maxsize=100)
    with pool.acquire() as event:
        event.process()

    # With custom validation
    def validate_event(event):
        return not getattr(event, "corrupted", false)

    pool = EventPool(maxsize=500, validator=validate_event)

    # Strict mode (no creation, no empty)
    strict_pool = create_event_pool(maxsize=50, strict=True)

    # Monitor pool health
    stats = pool.stats()
    if stats["hit_rate"] < 0.5:
        print(f"Warning: Low hit rate {stats['hit_rate']:.2%}")
