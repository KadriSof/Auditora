from types import MappingProxyType
from typing import NamedTuple, cast


class EventRecord(NamedTuple):
    """A record of an event that has occurred in the system.

    Attributes:
        etype (str): The type of event (e.g., 'login', 'file_access').
        timestamp (str): The time the event occurred, in ISO 8601 format.
        metadata (dict): Additional details about the event.
    """

    etype: str
    timestamp: str
    metadata: dict

    def __new__(cls, etype: str, timestamp: str, metadata: dict):
        """Create a new EventRecord with immutable metadata"""
        immutable_metadata = cast(dict, MappingProxyType(metadata))
        return super().__new__(cls, (etype, timestamp, immutable_metadata))
