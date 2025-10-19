from src.auditora.aspects.benchmarks.baseline import track_events_basic


def benchmark_with_memory():
    import tracemalloc
    tracemalloc.start()

    # Run basic benchmark
    track_events_basic(10000)

    current, peak = tracemalloc.get_traced_memory()
    print(f"Peak memory: {peak / 1024:.2f} KB")

if __name__ == "__main__":
    benchmark_with_memory()