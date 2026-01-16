"""Rate limiter utility to prevent OpenAI API rate limit errors."""

import asyncio
import logging
import time
from functools import wraps
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

# Track rate limit errors to adjust behavior
_rate_limit_count = 0
_last_rate_limit_time: Optional[float] = None


class RateLimiter:
    """Rate limiter to control API call frequency."""

    def __init__(self, min_interval_seconds: float = 1.0):
        """
        Initialize rate limiter.

        Args:
            min_interval_seconds: Minimum interval in seconds between API calls
        """
        self.min_interval = min_interval_seconds
        self.last_call_time: Optional[float] = None
        self._lock = asyncio.Lock()

    async def wait_if_needed(self) -> None:
        """Wait if necessary to respect the minimum interval between calls."""
        global _rate_limit_count, _last_rate_limit_time
        
        # Don't create a new span here - it should be created by the caller
        # This ensures proper hierarchy (span will be child of executor span)
        async with self._lock:
            current_time = time.time()
            
            # If we recently hit rate limits, add extra delay
            extra_delay = 0.0
            if _last_rate_limit_time is not None:
                time_since_rate_limit = current_time - _last_rate_limit_time
                if time_since_rate_limit < 60:  # Within last minute
                    # Add extra delay based on recent rate limit count
                    extra_delay = min(_rate_limit_count * 0.5, 5.0)  # Max 5 seconds extra
            
            if self.last_call_time is not None:
                elapsed = current_time - self.last_call_time
                required_interval = self.min_interval + extra_delay
                
                if elapsed < required_interval:
                    wait_time = required_interval - elapsed
                    
                    if wait_time > 0.1:  # Only log if significant wait
                        logger.info(
                            f"[RATE LIMIT] Waiting {wait_time:.2f}s | "
                            f"Base: {self.min_interval}s, Extra: {extra_delay:.2f}s | "
                            f"Elapsed: {elapsed:.2f}s"
                        )
                    await asyncio.sleep(wait_time)
                else:
                    logger.debug(
                        f"[RATE LIMIT] No wait needed | "
                        f"Elapsed: {elapsed:.2f}s >= Required: {required_interval:.2f}s"
                    )
            else:
                logger.debug(f"[RATE LIMIT] First call, no wait needed")
            
            self.last_call_time = time.time()

    async def __call__(self, func: Callable) -> Any:
        """Call function with rate limiting."""
        await self.wait_if_needed()
        return await func()


# Global rate limiter instance
_global_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get or create the global rate limiter instance."""
    global _global_rate_limiter
    if _global_rate_limiter is None:
        # Import here to avoid circular dependency
        import src.config as config
        interval = getattr(config, "RATE_LIMIT_INTERVAL_SECONDS", 1.0)
        _global_rate_limiter = RateLimiter(min_interval_seconds=interval)
    return _global_rate_limiter


def rate_limited(func: Callable) -> Callable:
    """
    Decorator to rate limit async functions.

    Usage:
        @rate_limited
        async def my_api_call():
            ...
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        limiter = get_rate_limiter()
        await limiter.wait_if_needed()
        return await func(*args, **kwargs)
    
    return wrapper


def record_rate_limit_error() -> None:
    """Record that a rate limit error occurred."""
    global _rate_limit_count, _last_rate_limit_time
    
    from agent_framework.observability import get_tracer
    from opentelemetry.trace import SpanKind, Status, StatusCode
    
    tracer = get_tracer()
    with tracer.start_as_current_span(
        "rate_limit.error",
        kind=SpanKind.INTERNAL,
    ) as span:
        _rate_limit_count += 1
        _last_rate_limit_time = time.time()
        
        span.set_status(Status(StatusCode.ERROR, "Rate limit exceeded"))
        span.set_attribute("rate_limit.error_count", _rate_limit_count)
        span.set_attribute("rate_limit.error_time", _last_rate_limit_time)
        
        logger.warning(
            f"[RATE LIMIT ERROR] Count: {_rate_limit_count} | "
            f"Increasing delays between calls"
        )
        
        # Reset counter after 5 minutes
        if _rate_limit_count > 10:
            logger.warning(
                f"[RATE LIMIT WARNING] Multiple errors ({_rate_limit_count}) detected. "
                f"Consider increasing RATE_LIMIT_INTERVAL_SECONDS."
            )
            span.set_attribute("rate_limit.severe", True)
