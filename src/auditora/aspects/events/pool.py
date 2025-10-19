import queue
from contextlib import contextmanager

from src.auditora.aspects.events.record import EventRecord


class EventPool:
    def __init__(self, maxsize: int = 1000):
        self._pool = queue.SimpleQueue()
        self._maxsize = maxsize

    @contextmanager
    def acquire(self):
        if not self._pool.empty():
            event = self._pool.get()
            event.clear()  # Hum..?
        else:
            event = EventRecord.__new__(EventRecord)

        try:
            yield event
        finally:
            if self._pool.qsize() < self._maxsize:
                self._pool.put(event)
