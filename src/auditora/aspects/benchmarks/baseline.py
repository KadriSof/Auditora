import statistics
import time

from src.auditora import sentinel, monitor, session
from src.auditora.adats.monitor import DefaultMonitor, OptimizedMonitor
from src.auditora.adats.session import DefaultSession

default_session = DefaultSession()

default_monitor = DefaultMonitor()
optimized_monitor = OptimizedMonitor()

@sentinel(session=default_session, monitor=optimized_monitor)
def track_events_basic(n_events: int):
    """Basic event tracking benchmark."""
    for i in range(n_events):
        large_metadata = {f'key_{j}': f'value_{j}' * 10 for j in range(20)}
        monitor.track(f"event_{i}", counter=i, value=i * 2.5, **large_metadata)
        # monitor.track(f"event_{i}", counter=i, value=i * 2.5)
        if i % 100 == 0:
            session.set(f"checkpoint_{i}", i)


def benchmark_basic():
    """Run basic performance benchmark."""
    n_events = 10000
    runs = 30
    results = []
    for i in range(runs):
        optimized_monitor.clear_buffer()
        default_session._state.clear()
        start_time = time.perf_counter()
        track_events_basic(n_events)
        end_time = time.perf_counter()
        results.append({
            'duration': end_time - start_time,
            'throughput': n_events / (end_time - start_time),
            'latency': (end_time - start_time) / n_events * 1_000_000
        })

    # Extract durations for mean calculation
    durations = [r['duration'] for r in results]
    duration = statistics.mean(durations)
    events_per_second = n_events / duration

    print("Basic Benchmark Results:")
    print(f"Events: {n_events:,}")
    print(f"Time: {duration:.4f} seconds")
    print(f"Throughput: {events_per_second:,.0f} events/second")
    print(f"Avg. time per event: {(duration / n_events) * 1_000_000:.2f} microseconds")

    # Get monitor stats
    monitor_obj = track_events_basic._monitor
    summary = monitor_obj.get_summary()
    print(f"Memory usage: {summary.get('buffer_usage', 0) * 100:.1f}% buffer utilization")



if __name__ == "__main__":
    benchmark_basic()