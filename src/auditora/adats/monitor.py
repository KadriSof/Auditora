"""
File: "src/auditora/adats/monitor.py"
Context: Monitor Adat - Advanced monitor for events tracking with timing and metrics.
"""
import time

from typing import Any, Dict, List


class DefaultMonitor:
    """Adat-2: Advanced monitor for events tracking with timing and metrics."""
    def __init__(self):
        self._events = []
        self._start_time = time.time()
        self._metrics = {}

    def track(self, event: str, duration: float | None = None, **metadata) -> Dict[str, Any]:
        """Track an event with optional timing and metadata."""
        timestamp = time.time()
        event_record = {
            'event': event,
            'timestamp': timestamp,
            'elapsed': timestamp - time.time(),
            **metadata,
        }
        if duration:
            event_record['duration'] = duration

        self._events.append(event_record)
        return event_record

    def start_timer(self, event: str) -> float:
        """Start a time for performance measurement."""
        self.track(event=f"{event}_started")
        return time.time()

    def stop_timer(self, event: str, start_time: float, **metadata) -> float:
        """Stop a time and automatically track the duration of the event."""
        duration : float = time.time() - start_time
        self.track(event=f"{event}_completed", duration=duration, **metadata)
        return duration

    def increment_metric(self, name: str, value: float = 1.0) -> None:
        """Increment a metric counter."""
        self._metrics[name] = self._metrics.get(name, 0) + value

    def get_events(self) -> List[Dict[str, Any]]:
        return self._events.copy()

    def get_metrics(self) -> Dict[str, Any]:
        return self._metrics.copy()

    def get_summary(self) -> Dict[str, Any]:
        """Get monitoring summary for reporting."""
        return {
            'total_events': len(self._events),
            'total_metrics': len(self._metrics),
            'events_by_type': self._count_events_by_type(),
            'metrics': self._metrics,
        }

    def _count_events_by_type(self) -> Dict[str, int]:
        counts = {}
        for event in self._events:
            event_type = event.get('event', 'unknown')
            counts[event_type] = counts.get(event_type, 0) + 1

        return counts

    def __str__(self) -> str:
        summary = self.get_summary()
        return f"<DefaultMonitor(events={summary['total_events']}, metrics={summary['total_metrics']})>"

    def __repr__(self) -> str:
        return self.__str__()
