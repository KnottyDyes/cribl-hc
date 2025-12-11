"""
Rate limiter with exponential backoff for API calls.

This module ensures the health check tool stays within the 100 API call budget
and implements exponential backoff for retry logic.
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Optional

from cribl_hc.utils.logger import get_logger


log = get_logger(__name__)


class RateLimiter:
    """
    Rate limiter with exponential backoff for API calls.

    Features:
    - Enforces maximum calls per time window
    - Exponential backoff for retries
    - Async-aware with proper lock handling
    - Tracks API call budget (100 calls max)

    Example:
        >>> limiter = RateLimiter(max_calls=100, time_window_seconds=300)
        >>> async with limiter:
        ...     response = await client.get("/api/endpoint")
    """

    def __init__(
        self,
        max_calls: int = 100,
        time_window_seconds: float = 300.0,
        enable_backoff: bool = True,
        initial_backoff_seconds: float = 1.0,
        max_backoff_seconds: float = 60.0,
        backoff_multiplier: float = 2.0,
    ):
        """
        Initialize rate limiter.

        Args:
            max_calls: Maximum number of calls allowed (default: 100)
            time_window_seconds: Time window in seconds (default: 300 = 5 minutes)
            enable_backoff: Whether to use exponential backoff (default: True)
            initial_backoff_seconds: Initial backoff delay (default: 1.0)
            max_backoff_seconds: Maximum backoff delay (default: 60.0)
            backoff_multiplier: Backoff multiplier (default: 2.0)
        """
        self.max_calls = max_calls
        self.time_window_seconds = time_window_seconds
        self.enable_backoff = enable_backoff
        self.initial_backoff_seconds = initial_backoff_seconds
        self.max_backoff_seconds = max_backoff_seconds
        self.backoff_multiplier = backoff_multiplier

        # Track API calls
        self.call_timestamps: list[datetime] = []
        self.total_calls_made = 0

        # Backoff state
        self.current_backoff_seconds = initial_backoff_seconds
        self.consecutive_failures = 0

        # Lock for thread-safe operations
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """
        Acquire permission to make an API call.

        This method blocks if rate limit is exceeded, waiting until a call slot is available.
        Implements exponential backoff if configured.

        Raises:
            RuntimeError: If maximum calls budget is exhausted
        """
        async with self._lock:
            # Check if budget exhausted
            if self.total_calls_made >= self.max_calls:
                raise RuntimeError(
                    f"API call budget exhausted ({self.total_calls_made}/{self.max_calls})"
                )

            # Remove timestamps outside the time window
            cutoff_time = datetime.utcnow() - timedelta(seconds=self.time_window_seconds)
            self.call_timestamps = [
                ts for ts in self.call_timestamps if ts > cutoff_time
            ]

            # Wait if rate limit exceeded
            while len(self.call_timestamps) >= self.max_calls:
                # Calculate wait time until oldest call expires
                oldest_call = min(self.call_timestamps)
                wait_until = oldest_call + timedelta(seconds=self.time_window_seconds)
                wait_seconds = (wait_until - datetime.utcnow()).total_seconds()

                if wait_seconds > 0:
                    log.info(
                        "rate_limit_wait",
                        wait_seconds=round(wait_seconds, 2),
                        calls_in_window=len(self.call_timestamps),
                    )
                    await asyncio.sleep(wait_seconds)

                # Re-check after wait
                cutoff_time = datetime.utcnow() - timedelta(
                    seconds=self.time_window_seconds
                )
                self.call_timestamps = [
                    ts for ts in self.call_timestamps if ts > cutoff_time
                ]

            # Record this call
            self.call_timestamps.append(datetime.utcnow())
            self.total_calls_made += 1

    def record_success(self) -> None:
        """
        Record a successful API call.

        Resets the backoff timer since the call succeeded.
        """
        self.consecutive_failures = 0
        self.current_backoff_seconds = self.initial_backoff_seconds

    async def record_failure(self, should_backoff: bool = True) -> None:
        """
        Record a failed API call and apply exponential backoff.

        Args:
            should_backoff: Whether to apply backoff delay (default: True)
        """
        self.consecutive_failures += 1

        if self.enable_backoff and should_backoff:
            # Calculate backoff delay
            backoff_delay = min(
                self.current_backoff_seconds * (self.backoff_multiplier ** (self.consecutive_failures - 1)),
                self.max_backoff_seconds,
            )

            log.warning(
                "api_call_failed_backoff",
                consecutive_failures=self.consecutive_failures,
                backoff_seconds=round(backoff_delay, 2),
            )

            await asyncio.sleep(backoff_delay)

            # Update backoff for next failure
            self.current_backoff_seconds = min(
                self.current_backoff_seconds * self.backoff_multiplier,
                self.max_backoff_seconds,
            )

    def get_remaining_calls(self) -> int:
        """
        Get number of remaining calls in the budget.

        Returns:
            Number of calls remaining (0 if budget exhausted)
        """
        return max(0, self.max_calls - self.total_calls_made)

    def get_calls_in_window(self) -> int:
        """
        Get number of calls made in the current time window.

        Returns:
            Number of calls in the current window
        """
        cutoff_time = datetime.utcnow() - timedelta(seconds=self.time_window_seconds)
        recent_calls = [ts for ts in self.call_timestamps if ts > cutoff_time]
        return len(recent_calls)

    def reset(self) -> None:
        """
        Reset the rate limiter state.

        Clears all tracking data and backoff state.
        """
        self.call_timestamps.clear()
        self.total_calls_made = 0
        self.consecutive_failures = 0
        self.current_backoff_seconds = self.initial_backoff_seconds

    async def __aenter__(self):
        """Async context manager entry."""
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        # Record success or failure based on exception
        if exc_type is None:
            self.record_success()
        else:
            # Don't backoff on exit since we're already done with the call
            await self.record_failure(should_backoff=False)
        return False  # Don't suppress exceptions


class SimpleSyncRateLimiter:
    """
    Simple synchronous rate limiter for non-async contexts.

    This is a simplified version for use in synchronous code.
    For full async support, use RateLimiter instead.
    """

    def __init__(self, max_calls: int = 100, time_window_seconds: float = 300.0):
        """
        Initialize simple synchronous rate limiter.

        Args:
            max_calls: Maximum calls allowed in time window
            time_window_seconds: Time window duration in seconds
        """
        self.max_calls = max_calls
        self.time_window_seconds = time_window_seconds
        self.call_timestamps: list[float] = []
        self.total_calls_made = 0

    def acquire(self) -> None:
        """
        Acquire permission to make a call (synchronous).

        Raises:
            RuntimeError: If budget exhausted or rate limit exceeded
        """
        if self.total_calls_made >= self.max_calls:
            raise RuntimeError(
                f"API call budget exhausted ({self.total_calls_made}/{self.max_calls})"
            )

        # Remove old timestamps
        current_time = time.time()
        cutoff_time = current_time - self.time_window_seconds
        self.call_timestamps = [ts for ts in self.call_timestamps if ts > cutoff_time]

        # Check rate limit
        if len(self.call_timestamps) >= self.max_calls:
            oldest_call = min(self.call_timestamps)
            wait_seconds = (oldest_call + self.time_window_seconds) - current_time
            raise RuntimeError(
                f"Rate limit exceeded. Wait {wait_seconds:.1f}s before next call."
            )

        # Record call
        self.call_timestamps.append(current_time)
        self.total_calls_made += 1

    def get_remaining_calls(self) -> int:
        """Get remaining calls in budget."""
        return max(0, self.max_calls - self.total_calls_made)
