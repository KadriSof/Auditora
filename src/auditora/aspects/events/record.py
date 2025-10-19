from typing import NamedTuple


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

    def update_metadata(self, metadata):
        self.metadata.update(metadata)
