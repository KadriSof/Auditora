"""
File: "src/auditora/adats/session.py"
Context: Session Adat - Session manager for state tracking.

Trivia: 'Adat' is the Arabic word for 'tool'. The plural is 'Adawat', but for simplicity I choose 'Adats')
"""
import uuid

from typing import Any, Dict, List
from datetime import datetime


class DefaultSession:
    """Adat-1: Advanced session manager for state tracking."""

    __slots__ = ('name', 'session_id', '_state', '_created_at', '_tags')

    def __init__(self, session_id: str = None, name: str | None = None) -> None:
        self.name = name or "default-session"
        self.session_id = session_id or str(uuid.uuid4())

        self._state = {}
        self._created_at = datetime.now()
        self._tags: List[str] = []

    def get(self, key: str, default: Any = None) -> Any:
        return self._state.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._state[key] = value

    def add_tag(self, tag: str) -> None:
        """Add metadata tags to the session."""
        if tag not in self._tags:
            self._tags.append(tag)

    def get_tags(self) -> List[str]:
        """Return list of metadata tags."""
        return self._tags

    def get_state_snapshot(self) -> Dict[str, Any]:
        """Get complete session state snapshot for debugging."""
        return {
            'session_id': self.session_id,
            'session_name': self.name,
            'created_at': self._created_at.isoformat(),
            'tags': self._tags,
            'state_keys': list(self._state.keys()),
        }

    def __str__(self) -> str:
        return f"<DefaultSession(name={self.name!r}, tags={self.get_tags()!r})>"

    def __repr__(self) -> str:
        return self.__str__()
