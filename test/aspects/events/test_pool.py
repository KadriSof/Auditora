"""
Test suite for EventPool - verifies pool behavior, data leakage prevention, and strict mode enforcement.
"""

import pytest
import time
import threading

from auditora.aspects.events.pool import (
    EventPool,
    PoolExhaustedError,
)
from auditora.aspects.events.builder import EventBuilder


class TestEventPoolCoreBehavior:
    """Test core pool functionality without data leakage concerns."""

    def test_pool_returns_clean_builders_on_acquisition(self):
        """Test that builders are always clean when acquired from pool"""
        pool = EventPool(maxsize=2)

        # First acquisition - should be clean
        with pool.acquire() as builder1:
            assert builder1.is_empty()
            builder1.set_type("test.1")
            builder1.set_metadata({"key": "value"})

        with pool.acquire() as builder2:
            assert builder2.is_empty()  # Builder should be clean
            assert builder2.peek_etype() == ""
            assert builder2.peek_metadata() == {}

    def test_pool_prevents_data_leakage_between_borrowers(self):
        """Test that data from one borrower never leaks to another"""
        pool = EventPool(maxsize=1)

        # Borrower 1 sets sensitive data
        with pool.acquire() as b1:
            b1.set_type("admin.login")
            b1.set_metadata({"password": "secret123", "user": "admin"})
            b1.set_timestamp("2026-02-02T00:00:00Z")
            b1.build()

        # Borrower 2 should get a completely clean builder
        with pool.acquire() as b2:
            # Verify no stale data remains
            assert b2.peek_etype() == ""
            assert b2.peek_timestamp() == ""
            assert b2.peek_metadata() == {}

            # Set new data
            b2.set_type("user.logout")
            b2.set_metadata({"user": "normal-user"})

            # Verify new data is correct and no old data remains
            assert b2.peek_etype() == "user.logout"
            assert "password" not in b2.peek_metadata()
            assert b2.peek_metadata().get("user") == "normal-user"

    def test_pool_returns_empty_builders_to_pool(self):
        """Test that empty builders are properly returned to the pool (identity check fix)"""
        pool = EventPool(maxsize=1)

        # Use a builder and clear it before exit
        with pool.acquire() as builder:
            builder.set_type("test")
            builder.build()
            builder.clear()  # Builder becomes empty

        assert pool.size == 0  # If not 0, empty builder was not returned to the pool

        # Next acquisition should succeed with a clean builder
        with pool.acquire() as builder2:
            assert builder2.is_empty()
            builder2.set_type("new.event")
            assert builder2.peek_etype() == "new.event"

    def test_pool_handles_exception_without_leaking(self):
        """Test that builders are properly returned even when exceptions occur"""
        pool = EventPool(maxsize=1)

        # Exception during usage
        try:
            with pool.acquire() as builder:
                builder.set_type("test")
            raise RuntimeError("Simulated Error")
        except RuntimeError:
            pass

        # Builder should be back in pool despite exceptions
        assert pool.size == 1  # If 0, builder not returned after exception
        assert pool.active_count == 0  # Builder still active

        # Should be able to acquire again
        with pool.acquire() as builder2:
            assert builder2.is_empty()
            builder2.set_type("recovery.event")

    def test_pool_active_tracking_accuracy(self):
        """Test that active tracking accurately reflects borrowed builders"""
        pool = EventPool(maxsize=2)

        assert pool.active_count == 0

        # Acquire one builder
        with pool.acquire() as b1:
            assert pool.active_count == 1
            b1.set_type("test1")

            with pool.acquire() as b2:
                assert pool.active_count == 2
                b2.set_type("test.2")

            # After inner context exits, active count shoud decrease
            assert pool.active_count == 1

        # After outer context exits
        assert pool.active_count == 0


class TestEventPoolDataLeakagePrevention:
    """Specialized tests for data leakage scenarios"""

    def test_no_cross_contamination_with_metadata_updates(self):
        """Test that partial metadata updates don't preserve old keys"""
        pool = EventPool(maxsize=1)

        # First borrower sets multiple keys
        with pool.acquire() as b1:
            b1.set_metadata({"key1": "value1", "key2": "value2", "key3": "value3"})

        # Second borrower only sets one key
        with pool.acquire() as b2:
            assert b2.peek_metadata() == {}
            b2.set_type("event.two")
            b2.set_metadata({"key1": "new-value"})

            metadata = b2.peek_metadata()

            assert len(metadata) == 1  # Expected 1 key
            assert metadata.get("key1") == "new-value"
            assert "key2" not in metadata
            assert "key3" not in metadata

    def test_no_deep_nested_data_leakage(self):
        """Test that complex nested structures don't leak between borrowers"""
        pool = EventPool(maxsize=1)

        # First borrower set complex nested data
        with pool.acquire() as b1:
            complex_metadata = {
                "user": "admin",
                "nested": {"deep": "secret_value", "list": [1, 2, 3]},
            }
            b1.set_type("admin.action")
            b1.set_metadata(complex_metadata)

        # Second borrower should haven no trace of nested data
        with pool.acquire() as b2:
            assert b2.peek_metadata() == {}
            b2.set_type("simple.event")
            b2.set_metadata({"simple": "data"})

            metadata = b2.peek_metadata()
            assert "nested" not in metadata
            assert "deep" not in str(metadata)
            assert len(metadata) == 1

    def test_conccurent_borrowers_no_cross_contamination(self):
        """Test that concurrent usage don't cause data leaks between threads"""
        pool = EventPool(maxsize=5)
        results = []
        errors = []
        lock = threading.Lock()

        def worker(worker_id: int, expected_value: str):
            try:
                with pool.acquire(timeout=2.0) as builder:
                    if not builder.is_empty():
                        errors.append(f"Worker {worker_id}: Got dirty builder!")
                        return

                    # Set unique data for this worker
                    builder.set_type(f"event.{worker_id}")
                    builder.set_metadata(
                        {"worker_id": worker_id, "value": expected_value}
                    )

                    # Verify our data is set correctly
                    assert builder.peek_metadata().get("worker_id") == worker_id
                    assert builder.peek_metadata().get("value") == expected_value

                    # Simulate work
                    time.sleep(0.01)

                    with lock:
                        results.append(
                            {
                                "worker_id": worker_id,
                                "metadata": builder.peek_metadata().copy(),
                            }
                        )
            except Exception as e:
                errors.append(f"Worker {worker_id}: {str(e)}")

        # Run multiple threads with different data
        threads = []
        for i in range(10):
            t = threading.Thread(target=worker, args=(i, f"secret_value_{i}"))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0  # Errors count should be 0

        # Verify each worker got its own data with no cross-contamination
        worker_data = {}
        for result in results:
            wid = result["worker_id"]
            assert wid not in worker_data  # Else worker ID appeared twice
            worker_data[wid] = result

        for i in range(10):
            assert worker_data[i]["metadata"]["worker_id"] == i
            assert worker_data[i]["metadata"]["value"] == f"secret_value_{i}"

    def test_metadata_is_deep_copied_on_set(self):
        """Test that metadata is deep copied to prevent external muatation"""
        pool = EventPool(maxsize=1)

        # External dictionary that might be mutated
        external_metadata = {"key": "value", "nested": {"inner": "data"}}

        with pool.acquire() as builder:
            builder.set_type("test")
            builder.set_metadata(external_metadata)

            # Mutate the external dictionary
            external_metadata["key"] = "changed"
            external_metadata["nested"]["inner"] = "mutated"

            # Builder metadata should remaim unchanged
            builder_metadata = builder.peek_metadata()
            assert builder_metadata.get("key") == "value"
            assert builder_metadata.get("nested", {}).get("inner") == "data"

    def test_builder_clear_called_on_return(self):
        """Test that builder.clear() is actually called when to pool"""
        pool = EventPool(maxsize=1)
        clear_called = False

        # Save original clear method
        original_clear = EventBuilder.clear

        def mock_clear(self):
            nonlocal clear_called
            clear_called = True
            original_clear(self)

        try:
            # Patch the clear method
            EventBuilder.clear = mock_clear

            # Use the pool
            with pool.acquire() as builder:
                builder.set_type("test")
                builder.set_metadata({"test": True})

            # Verify clear was called
            assert clear_called  # Else it was not called when returning to pool

        finally:
            # Restore original method
            EventBuilder.clear = original_clear


class TestEventPoolStrictMode:
    """Test strict mode functionality"""

    def test_strict_mode_raises_exhausted_error(self):
        """Test that strict mode raises PoolExhaustedError when pool is empty"""
        pool = EventPool(maxsize=1, strict=True)

        # Pre-populate the pool with a builder using 'force_new'
        with pool.acquire(force_new=True) as builder:
            builder.set_type("initial.event")

        # Verify pool has one idle builder
        assert pool.size == 1

        # Acquire the builder without returning it (the pool needs to stay empty)
        builder1 = pool.acquire().__enter__()
        builder1.set_type("first.event")

        assert pool.size == 0

        # With pool now empty, next acquire should raise PoolExhaustedError
        with pytest.raises(PoolExhaustedError) as exc_error:
            with pool.acquire(timeout=0.1) as builder:
                builder.set_type("should.fail")

        assert "exhausted" in str(exc_error.value).lower()
        assert "maxsize=1" in str(exc_error.value)

        pool._return_to_pool(builder1)

    def test_non_strict_mode_creates_new_objects(self):
        """Test that non-strict mode creates new objects when pool is empty"""
        pool = EventPool(maxsize=1, strict=False)

        # Hold the builder so it doesn't return to the pool
        builder1 = pool.acquire().__enter__()
        builder1.set_type("first.event")

        assert pool.size == 0
        assert pool.active_count == 1

        # Pool empty but non-strict should create new
        stats_before = pool.stats()
        assert stats_before["total_created"] == 1  # One created so far
        assert stats_before["total_reused"] == 0

        # Second acquire - should create new because pool is empty
        with pool.acquire() as builder2:
            builder2.set_type("second.event")

        stats_after = pool.stats()

        assert stats_after["total_created"] == 2
        assert stats_after["total_reused"] == 0

        pool._return_to_pool(builder1)

    def test_force_new_bypass_strict_mode(self):
        """Test that 'force_new=True bypass strict mode restriction"""
        pool = EventPool(maxsize=1, strict=True)

        # Even in strict mode 'force_new' should create new builder
        with pool.acquire(force_new=True) as builder:
            builder.set_type("forced.event")
            assert builder.peek_etype() == "forced.event"

        # Original idle builder should still be in the pool
        # (since we forced new, we didn't take from pool)
        assert pool.size == 1


class TestEventPoolPerformanceAndStats:
    """Test pool performance metrics and statistcs"""

    def test_pool_statistics_accuracy(self):
        """Test that pool statistics accurately reflects operations"""
        pool = EventPool(maxsize=2)

        # First acquisition - creates new
        with pool.acquire() as b:
            b.set_type("event.1")

        stats1 = pool.stats()
        assert stats1["total_created"] == 1
        assert stats1["total_reused"] == 0
        assert stats1["idle"] == 1

        # Second acquisition - reuses
        with pool.acquire() as b:
            b.set_type("event.2")

        stats2 = pool.stats()
        assert stats2["total_created"] == 1
        assert stats2["total_reused"] == 1
        assert stats2["idle"] == 1

        # Hit rate calculation
        assert stats2["hit_rate"] == 0.5  # 1 reuse / 2 total

    def test_pool_clear_method(self):
        """Test that 'pool.clear() removes idle builders"""
        pool = EventPool(maxsize=5)

        # Create some idle builders
        for i in range(3):
            with pool.acquire() as b:
                b.set_type(f"event.{i}")

        initial_size = pool.size
        assert initial_size > 0

        pool.clear()

        with pool.acquire(force_new=True) as b:
            b.set_type("new.event")
            assert b.peek_etype() == "new.event"

        assert pool.size >= 0


class TestEventPoolEdgeCases:
    """Test edge cases and error conditions."""

    def test_pool_with_maxsize_zero(self):
        """Test that maxsize < 1 raises ValueError."""
        with pytest.raises(ValueError, match="maxsize must be >= 1"):
            EventPool(maxsize=0)

        with pytest.raises(ValueError):
            EventPool(maxsize=-1)

    def test_pool_with_negative_timeout(self):
        """Test that negative timeout raises ValueError."""
        with pytest.raises(ValueError, match="timeout must be >= 0"):
            EventPool(timeout=-1.0)

    def test_pool_reuse_after_clear(self):
        """Test that pool works correctly after manual clear."""
        pool = EventPool(maxsize=2)

        # Use some builders
        for i in range(5):
            with pool.acquire() as b:
                b.set_type(f"event.{i}")

        # Clear the pool
        pool.clear()
        assert pool.size == 0

        # Should still work
        with pool.acquire() as b:
            b.set_type("after.clear")
            assert b.peek_etype() == "after.clear"

        assert pool.size == 1
