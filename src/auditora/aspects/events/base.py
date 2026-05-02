"""
Base types and protocols for the event system.
This module has NO external dependencies to avoid circular imports.
"""

from typing import Protocol, Any, Dict, Optional


class EventRecordProtocol(Protocol):
    """Protocol defining the EventRecord interface."""

    etype: str
    timestamp: str
    metadata: Any


class EventBuilderProtocol(Protocol):
    """Protocol defining the EventBuilder interface."""

    def set_type(self, etype: str) -> "EventBuilderProtocol": ...

    def set_timestamp(
        self, timestamp: Optional[str] = None
    ) -> "EventBuilderProtocol": ...

    def set_metadata(self, metadata: Dict[str, Any]) -> "EventBuilderProtocol": ...

    def update_metadata(self, metadata: Dict[str, Any]) -> "EventBuilderProtocol": ...

    def build(self) -> EventRecordProtocol: ...

    def clear(self) -> None: ...

    def is_empty(self) -> bool: ...


class EventPoolProtocol(Protocol):
    """Protocol defining the EventPool interface."""

    def acquire(self, timeout: Optional[float] = None, force_new: bool = False): ...

    def stats(self) -> Dict[str, Any]: ...

    def clear(self) -> None: ...

    @property
    def size(self) -> int: ...

    @property
    def active_count(self) -> int: ...
