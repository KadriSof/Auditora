"""
Immutable EventRecord definition - bottom layer with no dependencies.
"""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Dict, Any, Optional


@dataclass(frozen=True)
class EventRecord:
    """
    Immutable event record.
    This is the core data structure with no external dependencies.
    """

    etype: str
    timestamp: str
    metadata: MappingProxyType[str, Any]

    @classmethod
    def create(
        cls, etype: str, timestamp: str, metadata: Optional[Dict[str, Any]] = None
    ) -> "EventRecord":
        """Factory method with immutable metadata."""
        if metadata is None:
            metadata = {}
        return cls(
            etype=etype, timestamp=timestamp, metadata=MappingProxyType(metadata.copy())
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "etype": self.etype,
            "timestamp": self.timestamp,
            "metadata": dict(self.metadata),
        }
