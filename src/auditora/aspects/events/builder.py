"""
Mutable builder for immutable EventRecord objects with pooling support.

This module provides a fluend builder pattern implementation optimized for
object pooling scenarios where EventRecord must remain immutable but
allocation overhead needs to be minimized
"""

from datetime import datetime, timezone

from typing import Any

from auditora.aspects.events.record import EventRecord


class EventBuilder:
    """
    Mutable builder for creating immutable EventRecord instances.

    This builder is designed for object pooling - it can be cleared and reused
    multiple times without reallocation. The fluent interface allows chained
    method calls for concise event construction.

    Desing patterns:
        - Builder: Constructs complex EventRecord objects
        - Fluent interface: Method chaining for readability
        - Poolable: clear() method enables object reuse

    Performance characteristics:
        - __slot__ reduces memory footprint by ~50%
        - Lazy timestamp generation (only when needed)
        - Shallow metadata copy (caller can deep copy if required)
        - No exception overhead in normal operation

    Example:
    >>> builder = EventBuilder()
    >>> event = builder
    ... .set_type("user.login")
    ... .set_timestamp()
    ... .set_metadata({"user_id": 123})
    ... .build()
    >>> builder.clear()  # Ready for pool reuse
    """

    __slots__ = ("_etype", "_timestamp", "_metadata", "_built")

    # Timestamp format cache (class-level constant)

    def __init__(self) -> None:
        """Initialize a new empty builder"""
        self._etype: str = ""
        self._timestamp: str = ""
        self._metadata: dict[str, Any] = {}
        self._built: bool = False

    def set_type(self, etype: str) -> "EventBuilder":
        """
        Set the event type.

        Args:
            etype (str): Event type identifier (e.g., 'login', 'file_access')

        Returns:
            self for method chaining

        Raises:
            ValueError: if etype is empty or None
        """
        if not etype:
            raise ValueError("Event type cannot be empty")

        self._etype = etype
        self._built = False

        return self

    def set_timestamp(self, timestamp: str | None = None) -> "EventBuilder":
        """
        Set the event timestamp

        Args:
            timestamp: ISO format timestamp string. If None, current UTC time is used.

        Returns:
            self for method chaining

        Note:
            Uses UTC time for consistency across distributed systems.
        """
        if timestamp is None:
            # Generate timestamp efficiently without strftime overhead
            now = datetime.now(timezone.utc)
            timestamp = now.isoformat(timespec="milliseconds").replace("+00:00", "Z")

        elif not isinstance(timestamp, str):
            raise TypeError(
                f"Timestamp must be str or None, got {type(timestamp).__name__}"
            )

        self._timestamp = timestamp
        self._built = False
        return self

    def set_metadata(self, metadata: dict[str, Any]) -> "EventBuilder":
        """
        Replace entire metadata dictionary.

        Args:
            metadata: New metadata dictionary (will be copied)

        Returns:
            self for method chaining

        """
        if not isinstance(metadata, dict):
            raise TypeError(f"Metadata must be dict, got {type(metadata).__name__}")

        # Deep copy to prevent external mutation
        from copy import deepcopy

        self._metadata.clear()
        self._metadata.update(deepcopy(metadata))
        self._built = False
        return self

    def update_metadata(self, metadata: dict[str, Any]) -> "EventBuilder":
        """
        Update metadata with new key-value pairs.

        Args:
            metadata: Dictionary of metadata to merge

        Returns:
            self for method chaining

        Example:
        >>> builder.update_metadata({"user_id": 123, "ip": "10.10.10.1"})
        """
        if not isinstance(metadata, dict):
            raise TypeError(f"Metadata must be dict, got {type(metadata).__name__}")

        from copy import deepcopy

        self._metadata.update(deepcopy(metadata))
        self._built = False
        return self

    def build(self) -> EventRecord:
        """
        Build immutable EventRecord from current builder state.

        Returns:
            Immutable EventRecord instance

        Raises:
            RuntimeError: If required fields are missing (etype is required)

        Note:
            - Metadata is shallow copier to preserve immutability
            - Builder remains usable for more builds (but typically cleared after)
        """
        from auditora.aspects.events.record import EventRecord

        # Validation
        if not self._etype:
            raise RuntimeError("Cannot build EventRecord: etype not set")

        if not self._timestamp:
            # Auto-generate timestamp if missing
            self.set_timestamp()

        # Create immutable event with copied metadata
        event = EventRecord.create(
            etype=self._etype, timestamp=self._timestamp, metadata=self._metadata.copy()
        )

        self._built = True
        return event

    def clear(self) -> None:
        """
        Reset builder to initial empty state for pool reuse.

        This method is designed for object pooling - it reuses existing
        dictionary objects to minimize allocation overhead.

        Performance note:
            - Reuses _metadata dict (clear, don't reassign)
            - String fields reassigned to empty strings
            - No new objects created during clear
        """
        self._etype = ""
        self._timestamp = ""
        self._metadata.clear()
        self._built = False

    def is_empty(self) -> bool:
        """
        Check if builder has no data set.

        Returns:
            True if no fields have been set (except defaults)
        """
        return not (self._etype or self._timestamp or self._metadata)

    def has_data(self) -> bool:
        """
        Check if builder has any data set.

        Returns:
            True if any field has been configured
        """
        return not self.is_empty()

    def peek_etype(self) -> str:
        """Get current event type without building."""
        return self._etype

    def peek_timestamp(self) -> str:
        """Get current timestamp without building."""
        return self._timestamp

    def peek_metadata(self) -> dict[str, Any]:
        """Get copy of current metadata without building."""
        return self._metadata.copy()

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        status = "built" if self._built else "dirty"
        return (
            f"EventBuilder(etype={self._etype!r}, "
            f"timestamp={self._timestamp!r}, "
            f"metadata_keys={len(self._metadata)}, "
            f"status={status})"
        )

    def __len__(self) -> int:
        """Return number of metadata fields."""
        return len(self._metadata)

    def __bool__(self) -> bool:
        """Builder is truthy if it has data."""
        return self.has_data()


# Optional: Factory function for common builder configurations
def create_builder(
    etype: str | None = None,
    timestamp: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> EventBuilder:
    """

    Create and configure an EventBuilder in one call.

    This factory function is useful for scenarios where pooling is not needed
    or for testing.

    Args:
        etype: Event type
        timestamp: ISO timestamp (auto-generates if None)
        metadata: Initial metadata dictionary

    Returns:
        Configured EventBuilder instance

    Example:
    >>> builder = create_builder("login", metadata={"user": "alice"})
    >>> event = builder.build()
    """
    builder = EventBuilder()

    if etype:
        builder.set_type(etype)
    if metadata:
        builder.set_metadata(metadata)
    if timestamp is not None or (etype and not timestamp):
        # Set timestamp if explicitly provided or if we have type but no timestamp
        builder.set_timestamp(timestamp)

    return builder


# Helper for batch building
class EventBatchBuilder:
    """
    Build multiple events efficiently from a single builder instance.

    Useful for scenarios where many similar events are created.

    Example:
        >>> batch = EventBatchBuilder()
        >>> events = batch.create_batch([
        ...     {"etype": "click", "metadata": {"x": 100, "y": 200}},
        ...     {"etype": "click", "metadata": {"x": 150, "y": 250}},
        ... ])
    """

    __slots__ = ("_builder",)

    def __init__(self) -> None:
        """Initialize batch builder with a reusable builder instance."""
        self._builder = EventBuilder()

    def create_batch(self, configs: list) -> list:
        """
        Create multiple events from configuration dictionaries.

        Args:
            configs: List of dicts with 'etype', 'timestamp', 'metadata' keys

        Returns:
            List of EventRecord instances
        """
        events = []

        for config in configs:
            self._builder.clear()

            if "etype" in config:
                self._builder.set_type(config["etype"])
            if "timestamp" in config:
                self._builder.set_timestamp(config["timestamp"])
            if "metadata" in config:
                self._builder.update_metadata(config["metadata"])

            events.append(self._builder.build())

        return events
