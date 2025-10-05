"""
File: "src/auditora/adats/monitor.py"
Context: Monitor Adat - Advanced monitor for events tracking with timing and metrics.
"""
from array import array
from typing import Any, Dict, List, Deque

from src.auditora.aspects.events.record import EventRecord


class DefaultMonitor:
    """Adat-2: Advanced monitor for events tracking with timing and metrics."""

    __slots__ = (
        '_start_time', '_event_count', '_max_buffer_size',
        '_events_buffer', '_events_metadata', '_metrics'
    )
    def __init__(self, max_buffer_size: int = 10000):
        self._start_time = time.perf_counter()
        self._event_count = 0
        self._max_buffer_size = max_buffer_size

        # Pre-allocate buffers for maximum efficiency
        self._events_buffer = array('d', [0.0] * max_buffer_size)  # Timestamps
        self._events_metadata: Deque[EventRecord] = deque(maxlen=max_buffer_size)
        self._metrics: Dict[str, float] = {}

    def track(self, event: str, duration: float | None = None, **metadata) -> None:
        """Event fast tracking with minimal allocation."""
        if self._event_count >= self._max_buffer_size:
            # Handle buffer overflow (e.g., flush to disk, send to external system, dropt oldest events, etc.)
            return

        current_time = time.perf_counter()
        elapsed = current_time - self._start_time

        # Store event timestamp in pre-allocated array (zero-allocation)
        self._events_buffer[self._event_count] = elapsed

        event_record = EventRecord(
            etype=event,
            timestamp=elapsed,
            metadata=metadata
        )

        if duration is not None:
            event_record.details['duration'] = duration

        event_record.update_metadata(metadata)

        self._events_metadata.append(event_record)
        self._event_count += 1

    def start_timer(self, event: str) -> float:
        """Start a time for performance measurement."""
        self.track(event=f"{event}_started")
        return time.perf_counter()

    def stop_timer(self, event: str, start_time: float, **metadata) -> float:
        """Stop a time and automatically track the duration of the event."""
        duration : float = time.perf_counter() - start_time
        self.track(event=f"{event}_completed", duration=duration, **metadata)
        return duration

    def increment_metric(self, name: str, value: float = 1.0) -> None:
        """Increment a metric counter."""
        self._metrics[name] = self._metrics.get(name, 0.0) + value

    def get_events(self) -> List[EventRecord]:
        return list(self._events_metadata)

    def get_metrics(self) -> Dict[str, Any]:
        return self._metrics.copy()

    def get_summary(self) -> Dict[str, Any]:
        """Get monitoring summary for reporting."""
        events_list = self.get_events()
        event_types = self._count_events_by_type()

        return {
            'total_events': len(events_list),
            'total_metrics': len(self._metrics),
            'events_by_type': event_types,
            'metrics': self._metrics.copy(),
            'buffer_usage': self._event_count / self._max_buffer_size
        }

    def serialize_events(self) -> bytes:
        """Serialize events to bytes using MessagePack."""
        events_data = {
            'events': [event._asdict() for event in self._events_metadata],
            'start_time': self._start_time,
            'event_count': self._event_count
        }
        return msgpack.packb(events_data, use_bin_type=True)

    def clear_buffer(self) -> None:
        """Clear the events buffer."""
        self._events_metadata.clear()
        self._event_count = 0

    def _count_events_by_type(self) -> Dict[str, int]:
        events = self.get_events()
        counts = {}

        if isinstance(events[-1], dict):
            for event in events:
                event_type = event.get('event', 'N/A')
                counts[event_type] = counts.get(event_type, 0) + 1

            return counts

        for event in events:
            event_type = event.etype
            counts[event_type] = counts.get(event_type, 0) + 1

        return counts

    def __str__(self) -> str:
        summary = self.get_summary()
        return f"<DefaultMonitor(events={summary['total_events']}, metrics={summary['total_metrics']})>"

    def __repr__(self) -> str:
        return self.__str__()


import msgpack
import time
from typing import Dict, Any, List
from collections import deque


class OptimizedMonitor(DefaultMonitor):
    """Optimized monitor with reduced memory footprint (penalty to throughput)."""

    __slots__ = (
        '_event_count', '_events_buffer', '_pending_events', '_metrics_cache', '_buffer_header'
    )

    def __init__(self, max_buffer_size: int = 10000):
        """
        Initialize the optimized monitor.

        Args:
            max_buffer_size (int): Maximum number of events to buffer (before overflow).
        """
        super().__init__(max_buffer_size)
        self._event_count = 0

        self._events_buffer = bytearray()
        self._pending_events = []
        self._metrics_cache = {}

        # Header for versioning and metadata
        self._buffer_header = msgpack.packb({
            'version': 1,
            'created_at': time.time(),
            'format': 'msgpack'
        })

    def track(self, event: str, duration: float | None = None, **metadata) -> None:
        """
        Serialize to bytes immediately, defer parsing.

        Args:
            event (str): Event name/type.
            duration (float | None): Optional duration of the event in seconds.
            **metadata: Additional metadata for event context.

        Note:
            Returns nothing; events are stored in a byte buffer for later parsing.
        """
        if self._event_count >= self._max_buffer_size:
            # Handle buffer overflow - could flush to disk here
            return

        event_bytes = self._serialize_event(event, duration, metadata)
        self._events_buffer.extend(event_bytes)
        self._event_count += 1

    def get_events(self) -> List[Dict[str, Any]]:
        """
        Parse buffer into events only when requested.

        Returns:
            List[Dict[str, Any]]: List of parsed event dictionaries.

        Note:
            Implements lazy parsing to save memory and CPU until events are needed.
        """
        if not self._pending_events:
            self._pending_events = self._parse_buffer()

        return self._pending_events

    def get_summary(self) -> Dict[str, Any]:
        """
        Get monitoring summary for reporting.

        Returns:
            Dict[str, Any]: Summary including total events, buffer size, and compression ratio.
        """
        summary = super().get_summary()
        summary['total_events'] = self._event_count
        summary['buffer_size_bytes'] = len(self._events_buffer)
        summary['compression_ratio'] = self._calculate_compression_ratio()

        return summary

    def _serialize_event(self, event: str, duration: float | None, metadata: Dict) -> bytes:
        """
        Serialize a single event to compact binary format.

        Args:
            event (str): Event name/type.
            duration (float | None): Optional duration of the event in seconds.
            metadata (Dict): Additional metadata for event context.

        Returns:
            bytes: Serialized event in MessagePack format.

        Note:
            Uses short keys for maximum compression efficiency.
        """
        # Minimal event representation
        event_data = {
            'e': event,
            't': time.perf_counter() - self._start_time,
            'ts': time.time()
        }

        if duration is not None:
            event_data['d'] = float(duration)

        if metadata:
            event_data['m'] = metadata

        # Serialize with efficient settings
        return msgpack.packb(event_data, use_bin_type=True, strict_types=True)

    def _parse_buffer(self) -> List[Dict[str, Any]]:
        """
        Parse the entire byte buffer back into event objects.

        Returns:
            List[Dict[str, Any]]: List of parsed event dictionaries.

        Raises:
            msgpack.UnpackException: If the buffer contains corrupt msgpack data.

        Note:
            Uses memoryview and offset tracking for efficient parsing.
        """
        if not self._events_buffer:
            return []

        events = []
        buffer_view = memoryview(self._events_buffer)
        offset = 0

        try:
            while offset < len(buffer_view):
                # Use 'unpackb' with offset to efficiently parse multiple objects
                event_data, bytes_consumed = self._unpack_with_offset(data=buffer_view[offset:])

                if event_data is not None:
                    # Convert back to full field names for usability
                    full_event = self._deserialize_to_readable_format(event_data=event_data)
                    events.append(full_event)

                    offset += bytes_consumed

                else:
                    # If we can't parse further, break to avoid infinite loop
                    # TODO-0: Log warning about partial parsing and fallback to ?
                    break

        except (msgpack.UnpackException, ValueError) as e:
            print(f"Warning: Partial buffer parsing completed. Error: {e}")

        return events

    def _unpack_with_offset(self, data: memoryview) -> tuple:
        """
        Unpack a single msgpack object from buffer and return bytes consumed.

        Args:
            data (memoryview): The buffer slice to unpack from.

        Returns:
            tuple: (event_data: Dict | None, bytes_consumed: int)

        Raises:
            msgpack.UnpackException: If unpacking fails.
        """
        try:
            unpacker = msgpack.Unpacker(raw=False)
            unpacker.feed(data)

            for event_data in unpacker:
                bytes_consumed = unpacker.tell()
                return event_data, bytes_consumed

        except msgpack.UnpackException:
            # If unable to unpack, skip this event.
            return None, len(data)

    def _deserialize_to_readable_format(self, event_data: Dict) -> Dict[str, Any]:
        """
        Convert compact serialized format back to human-readable format.

        Args:
            event_data (Dict): The compact event data with short keys.

        Returns:
            Dict[str, Any]: Event data dict with full field names.
        """
        readable_event = {
            'event': event_data.get('e', ''),
            'timestamp': event_data.get('t', 0.0),
            'absolute_timestamp': event_data.get('ts', 0.0)
        }

        if 'd' in event_data:
            readable_event['duration'] = event_data['d']

        if 'm' in event_data:
            readable_event['metadata'] = event_data['m']

        return readable_event

    def _calculate_compression_ratio(self) -> float:
        """
        Calculate efficiency of serialization is comparison to raw Python objects.

        Returns:
            Ratio of serialized size to estimated Python object size.

        Note:
            Uses rough estimates of 200 bytes per Python dictionary object.
        """
        if not self._event_count:
            return 0.0

        estimated_python_size = self._event_count * 200  # ~200 bytes per Python dict
        actual_size = len(self._events_buffer)

        if estimated_python_size > 0:
            return actual_size / estimated_python_size

        return 0.0

    def flush_to_disk(self, filepath: str) -> None:
        """
        Efficiently flush buffer to disk without parsing.

        Args:
            filepath (str): Path to file where buffer should be saved.

        Raises:
            IOError: If file cannot be written.
        """
        with open(filepath, 'wb') as f:
            # Write header
            f.write(self._buffer_header)
            # Write event count
            f.write(msgpack.packb({'event_count': self._event_count}))
            # Write raw buffer
            f.write(self._events_buffer)

        # Clear buffer after flush
        self.clear_buffer()

    def load_from_disk(self, filepath: str) -> None:
        """
        Load previously flushed buffer from disk.

        Args:
            filepath (str): Path to file where buffer is stored.

        Raises:
            IOError: If file cannot be read.
            msgpack.UnpackException: if saved data is corrupt.
        """
        with open(filepath, 'rb') as f:
            header_data = f.read(len(self._buffer_header))
            header = msgpack.unpackb(header_data)

            event_count_data = msgpack.unpackb(f.read())
            self._events_buffer = bytearray(f.read())
            self._event_count = event_count_data['event_count']

        # Invalidate cached parsed events
        self._pending_events = []

    def clear_buffer(self) -> None:
        """Clear the events buffer and reset state."""
        self._events_buffer = bytearray()
        self._pending_events = []
        self._event_count = 0

    def get_buffer_stats(self) -> Dict[str, Any]:
        """
        Get detailed statistics about the serialized buffer.

        Returns:
            Dict[str, Any]: Statistics including size and efficiency metrics.
        """
        return {
            'total_events': self._event_count,
            'buffer_size_bytes': len(self._events_buffer),
            'bytes_per_event': len(self._events_buffer) / self._event_count if self._event_count else 0,
            'compression_ratio': self._calculate_compression_ratio(),
            'memory_usage_mb': len(self._events_buffer) / (1024 * 1024)
        }


class AsyncMonitor(DefaultMonitor):
    """Asynchronous monitor for high-throughput event tracking."""
    def __init__(self, queue_size: int = 1000):
        super().__init__()
        self._event_queue = deque(maxsize=queue_size)
        self._processor_task = None

    async def start_processor(self):
        """Start the background event processor."""
        import asyncio
        self._processor_task = asyncio.create_task(self._process_events())

    async def _process_events(self):
        import asyncio
        while True:
            event = await asyncio.to_thread(self._event_queue.get)
            # Process events (persist, send to external system, etc.)
            self._event_queue.task_done()

    def track(self, event: str, **metadata) -> None:
        """Enqueue event for asynchronous processing."""
        import asyncio
        try:
            self._event_queue.put_nowait((event, metadata))
        except asyncio.QueueFull:
            # Handle full queue (e.g., drop event, log warning, scale, etc.)
            pass
