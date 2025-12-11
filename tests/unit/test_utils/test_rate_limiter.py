"""
Unit tests for rate limiter functionality.
"""

import asyncio
import time

import pytest

from cribl_hc.utils.rate_limiter import RateLimiter, SimpleSyncRateLimiter


class TestRateLimiter:
    """Test async rate limiter."""

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test rate limiter initialization."""
        limiter = RateLimiter(max_calls=10, time_window_seconds=60.0)

        assert limiter.max_calls == 10
        assert limiter.time_window_seconds == 60.0
        assert limiter.total_calls_made == 0
        assert len(limiter.call_timestamps) == 0

    @pytest.mark.asyncio
    async def test_single_acquire(self):
        """Test acquiring single rate limit slot."""
        limiter = RateLimiter(max_calls=10, time_window_seconds=60.0)

        await limiter.acquire()

        assert limiter.total_calls_made == 1
        assert len(limiter.call_timestamps) == 1

    @pytest.mark.asyncio
    async def test_multiple_acquires(self):
        """Test multiple acquire calls."""
        limiter = RateLimiter(max_calls=5, time_window_seconds=60.0)

        for i in range(5):
            await limiter.acquire()

        assert limiter.total_calls_made == 5
        assert len(limiter.call_timestamps) == 5

    @pytest.mark.asyncio
    async def test_budget_exhaustion(self):
        """Test that budget exhaustion raises error."""
        limiter = RateLimiter(max_calls=3, time_window_seconds=60.0)

        # Use up budget
        await limiter.acquire()
        await limiter.acquire()
        await limiter.acquire()

        # Next call should fail
        with pytest.raises(RuntimeError) as exc_info:
            await limiter.acquire()

        assert "budget exhausted" in str(exc_info.value).lower()
        assert "3/3" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test rate limiter as async context manager."""
        limiter = RateLimiter(max_calls=10, time_window_seconds=60.0)

        async with limiter:
            pass  # Simulates successful API call

        assert limiter.total_calls_made == 1
        assert limiter.consecutive_failures == 0

    @pytest.mark.asyncio
    async def test_context_manager_with_exception(self):
        """Test rate limiter context manager with exception."""
        limiter = RateLimiter(max_calls=10, time_window_seconds=60.0, enable_backoff=False)

        try:
            async with limiter:
                raise ValueError("Test error")
        except ValueError:
            pass

        assert limiter.total_calls_made == 1
        assert limiter.consecutive_failures == 1

    @pytest.mark.asyncio
    async def test_record_success(self):
        """Test recording successful API call."""
        limiter = RateLimiter(max_calls=10, time_window_seconds=60.0)

        limiter.consecutive_failures = 5
        limiter.current_backoff_seconds = 10.0

        limiter.record_success()

        assert limiter.consecutive_failures == 0
        assert limiter.current_backoff_seconds == limiter.initial_backoff_seconds

    @pytest.mark.asyncio
    async def test_record_failure(self):
        """Test recording failed API call."""
        limiter = RateLimiter(
            max_calls=10,
            time_window_seconds=60.0,
            enable_backoff=False,  # Disable backoff for faster test
        )

        await limiter.record_failure(should_backoff=False)

        assert limiter.consecutive_failures == 1

    @pytest.mark.asyncio
    async def test_exponential_backoff(self):
        """Test exponential backoff on failures."""
        limiter = RateLimiter(
            max_calls=10,
            time_window_seconds=60.0,
            enable_backoff=True,
            initial_backoff_seconds=0.1,  # Short for testing
            max_backoff_seconds=1.0,
            backoff_multiplier=2.0,
        )

        start_time = time.time()
        await limiter.record_failure(should_backoff=True)
        elapsed = time.time() - start_time

        # Should have waited at least the initial backoff
        assert elapsed >= 0.1
        assert limiter.consecutive_failures == 1

    @pytest.mark.asyncio
    async def test_get_remaining_calls(self):
        """Test getting remaining calls."""
        limiter = RateLimiter(max_calls=10, time_window_seconds=60.0)

        assert limiter.get_remaining_calls() == 10

        await limiter.acquire()
        assert limiter.get_remaining_calls() == 9

        await limiter.acquire()
        await limiter.acquire()
        assert limiter.get_remaining_calls() == 7

    @pytest.mark.asyncio
    async def test_get_calls_in_window(self):
        """Test getting calls in current window."""
        limiter = RateLimiter(max_calls=100, time_window_seconds=1.0)  # 1 second window

        await limiter.acquire()
        await limiter.acquire()

        assert limiter.get_calls_in_window() == 2

        # Wait for window to expire
        await asyncio.sleep(1.1)

        assert limiter.get_calls_in_window() == 0

    @pytest.mark.asyncio
    async def test_reset(self):
        """Test resetting rate limiter."""
        limiter = RateLimiter(max_calls=10, time_window_seconds=60.0)

        await limiter.acquire()
        await limiter.acquire()
        limiter.consecutive_failures = 3

        limiter.reset()

        assert limiter.total_calls_made == 0
        assert len(limiter.call_timestamps) == 0
        assert limiter.consecutive_failures == 0
        assert limiter.current_backoff_seconds == limiter.initial_backoff_seconds

    @pytest.mark.asyncio
    async def test_time_window_expiration(self):
        """Test that calls expire after time window."""
        limiter = RateLimiter(max_calls=5, time_window_seconds=0.5)  # 500ms window

        # Make 5 calls (at limit)
        for _ in range(5):
            await limiter.acquire()

        assert limiter.get_calls_in_window() == 5

        # Wait for window to expire
        await asyncio.sleep(0.6)

        # Calls should have expired
        assert limiter.get_calls_in_window() == 0

        # Should be able to make more calls
        await limiter.acquire()
        assert limiter.get_calls_in_window() == 1


class TestSimpleSyncRateLimiter:
    """Test synchronous rate limiter."""

    def test_initialization(self):
        """Test sync rate limiter initialization."""
        limiter = SimpleSyncRateLimiter(max_calls=10, time_window_seconds=60.0)

        assert limiter.max_calls == 10
        assert limiter.time_window_seconds == 60.0
        assert limiter.total_calls_made == 0

    def test_single_acquire(self):
        """Test acquiring single slot."""
        limiter = SimpleSyncRateLimiter(max_calls=10, time_window_seconds=60.0)

        limiter.acquire()

        assert limiter.total_calls_made == 1

    def test_multiple_acquires(self):
        """Test multiple acquire calls."""
        limiter = SimpleSyncRateLimiter(max_calls=5, time_window_seconds=60.0)

        for _ in range(5):
            limiter.acquire()

        assert limiter.total_calls_made == 5

    def test_budget_exhaustion(self):
        """Test budget exhaustion."""
        limiter = SimpleSyncRateLimiter(max_calls=3, time_window_seconds=60.0)

        limiter.acquire()
        limiter.acquire()
        limiter.acquire()

        with pytest.raises(RuntimeError) as exc_info:
            limiter.acquire()

        assert "budget exhausted" in str(exc_info.value).lower()

    def test_rate_limit_exceeded(self):
        """Test rate limit per window."""
        limiter = SimpleSyncRateLimiter(max_calls=2, time_window_seconds=60.0)

        limiter.acquire()
        limiter.acquire()

        # Third call within window should fail
        with pytest.raises(RuntimeError) as exc_info:
            limiter.acquire()

        assert "rate limit exceeded" in str(exc_info.value).lower()

    def test_get_remaining_calls(self):
        """Test getting remaining calls."""
        limiter = SimpleSyncRateLimiter(max_calls=10, time_window_seconds=60.0)

        assert limiter.get_remaining_calls() == 10

        limiter.acquire()
        assert limiter.get_remaining_calls() == 9

        limiter.acquire()
        limiter.acquire()
        assert limiter.get_remaining_calls() == 7

    def test_time_window_cleanup(self):
        """Test that old timestamps are removed."""
        limiter = SimpleSyncRateLimiter(max_calls=10, time_window_seconds=0.1)  # 100ms window

        limiter.acquire()
        assert len(limiter.call_timestamps) == 1

        time.sleep(0.15)  # Wait for window to expire

        limiter.acquire()  # This should clean up old timestamps

        # Should only have 1 timestamp (the recent one)
        assert len(limiter.call_timestamps) == 1
        assert limiter.total_calls_made == 2


class TestRateLimiterEdgeCases:
    """Test edge cases and corner scenarios."""

    @pytest.mark.asyncio
    async def test_zero_max_calls(self):
        """Test rate limiter with zero max calls."""
        limiter = RateLimiter(max_calls=0, time_window_seconds=60.0)

        with pytest.raises(RuntimeError):
            await limiter.acquire()

    @pytest.mark.asyncio
    async def test_concurrent_acquires(self):
        """Test concurrent acquire calls."""
        limiter = RateLimiter(max_calls=10, time_window_seconds=60.0)

        # Launch multiple concurrent acquires
        tasks = [limiter.acquire() for _ in range(5)]
        await asyncio.gather(*tasks)

        assert limiter.total_calls_made == 5

    @pytest.mark.asyncio
    async def test_max_backoff_limit(self):
        """Test that backoff doesn't exceed maximum."""
        limiter = RateLimiter(
            max_calls=100,
            enable_backoff=True,
            initial_backoff_seconds=0.1,
            max_backoff_seconds=0.5,
            backoff_multiplier=10.0,  # Aggressive multiplier
        )

        # Trigger multiple failures
        for _ in range(5):
            await limiter.record_failure(should_backoff=False)

        # Backoff should be capped at max
        assert limiter.current_backoff_seconds <= 0.5
