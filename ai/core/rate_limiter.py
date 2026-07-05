# ai/core/rate_limiter.py
# imports
import time
import random
import threading
from typing import Optional, Callable, Any, Dict
from collections import defaultdict
import logging

# Base logger
logger = logging.getLogger("my_app")


# class Ratelimiter
class RateLimiter:
    """Smart rate limiter with exponential backoff and jitter"""

    def __init__(self):
        self.request_counts = defaultdict(int)
        self.last_request_time = defaultdict(float)
        self.backoff_times = defaultdict(float)
        self.lock = threading.Lock()
        # Configurable limits
        self.max_retries = 5
        self.base_delay = 1.0
        self.max_delay = 60.0
        self.jitter = 0.2
        self.rate_limit_window = 60  # seconds

    def _get_delay(self, attempt: int) -> float:
        # Exponential backoff: 1, 2, 4, 8, 16...
        delay = self.base_delay * (2**attempt)
        # Cap at max delay
        delay = min(delay, self.max_delay)
        # Add jitter to prevent thundering herd
        jitter = random.uniform(-self.jitter * delay, self.jitter * delay)
        delay = max(0.1, delay + jitter)
        return delay

    def _is_rate_limited(self, endpoint: str) -> bool:
        """Check if we're currently rate limited for an endpoint"""
        with self.lock:
            if endpoint not in self.backoff_times:
                return False
            wait_until = self.backoff_times[endpoint]
            if time.time() < wait_until:
                return True
            # Cooldown expired
            del self.backoff_times[endpoint]
            return False

    def _apply_backoff(self, endpoint: str, attempt: int):
        """Apply backoff for an endpoint"""
        delay = self._get_delay(attempt)
        wait_until = time.time() + delay
        with self.lock:
            self.backoff_times[endpoint] = wait_until
        logger.warning(f"Rate limited on {endpoint}, backing off for {delay:.2f}s")

    def execute_with_retry(
        self,
        func: Callable,
        endpoint: str,
        max_retries: Optional[int] = None,
        args: tuple = (),
        kwargs: dict = None,
    ) -> Any:
        if kwargs is None:
            kwargs = {}
        retries = max_retries or self.max_retries
        for attempt in range(retries + 1):
            try:
                # Check if we're rate limited
                if self._is_rate_limited(endpoint):
                    logger.debug(f"Waiting for rate limit cooldown on {endpoint}")
                    wait_until = self.backoff_times[endpoint]
                    sleep_time = max(0, wait_until - time.time())
                    time.sleep(sleep_time + 0.1)
                    continue
                # Execute function
                result = func(*args, **kwargs)
                # Reset backoff on success
                with self.lock:
                    if endpoint in self.backoff_times:
                        del self.backoff_times[endpoint]
                return result
            except Exception as e:
                status_code = None
                if hasattr(e, "response"):
                    status_code = (
                        e.response.status_code
                        if hasattr(e.response, "status_code")
                        else None
                    )
                # Check if it's a rate limit error
                is_rate_limit = False
                if status_code == 429:
                    is_rate_limit = True
                elif "429" in str(e) or "Too Many Requests" in str(e):
                    is_rate_limit = True
                elif "Rate limit exceeded" in str(e):
                    is_rate_limit = True
                if is_rate_limit and attempt < retries:
                    logger.warning(
                        f"Rate limit on {endpoint}, attempt {attempt + 1}/{retries + 1}"
                    )
                    self._apply_backoff(endpoint, attempt + 1)
                    continue
                # Not rate limit or max retries reached
                logger.error(
                    f"Request to {endpoint} failed after {attempt + 1} attempts: {e}"
                )
                raise

    def reset(self, endpoint: Optional[str] = None):
        """Reset rate limiter state for an endpoint or all"""
        with self.lock:
            if endpoint:
                self.backoff_times.pop(endpoint, None)
                self.request_counts.pop(endpoint, None)
                self.last_request_time.pop(endpoint, None)
            else:
                self.backoff_times.clear()
                self.request_counts.clear()
                self.last_request_time.clear()


class ModelRateLimiter(RateLimiter):
    """Rate limiter specifically for model endpoints"""

    def __init__(self):
        super().__init__()
        self.model_limits = defaultdict(
            lambda: {"limit": 50, "remaining": 50, "reset": 0}
        )
        self.global_limits = {"limit": 500, "remaining": 500, "reset": 0}

    def update_headers(self, endpoint: str, headers: Dict[str, str]):
        """Update rate limit info from response headers"""
        if endpoint == "global":
            target = self.global_limits
        else:
            target = self.model_limits[endpoint]
        if "X-RateLimit-Limit" in headers:
            target["limit"] = int(headers["X-RateLimit-Limit"])
        if "X-RateLimit-Remaining" in headers:
            target["remaining"] = int(headers["X-RateLimit-Remaining"])
        if "X-RateLimit-Reset" in headers:
            target["reset"] = int(headers["X-RateLimit-Reset"])

    def get_limits(self, endpoint: str = None) -> Dict[str, Any]:
        """Get current rate limits"""
        if endpoint:
            return dict(self.model_limits[endpoint])
        return dict(self.global_limits)

    def can_make_request(self, endpoint: str) -> bool:
        """Check if we can make a request to an endpoint"""
        limits = (
            self.get_limits(endpoint) if endpoint != "global" else self.global_limits
        )
        # If limit is 0, we're probably not rate limited
        if limits["limit"] == 0:
            return True
        # Check if reset time has passed
        if limits["reset"] > 0 and time.time() > limits["reset"]:
            limits["remaining"] = limits["limit"]
            limits["reset"] = 0
            return True

        return limits["remaining"] > 0


class RetryContext:
    """Context manager for retry operations"""

    def __init__(self, rate_limiter: RateLimiter, endpoint: str, max_retries: int = 3):
        self.rate_limiter = rate_limiter
        self.endpoint = endpoint
        self.max_retries = max_retries
        self.attempt = 0
        self.success = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with retry"""
        return self.rate_limiter.execute_with_retry(
            func=func,
            endpoint=self.endpoint,
            max_retries=self.max_retries,
            args=args,
            kwargs=kwargs,
        )


# Decorator for automatically retry
def retry_on_429(max_retries: int = 3, endpoint: Optional[str] = None):
    """Decorator to automatically retry on 429 errors"""
    rate_limiter = RateLimiter()

    def decorator(func):
        def wrapper(*args, **kwargs):
            actual_endpoint = endpoint or func.__name__
            return rate_limiter.execute_with_retry(
                func=func,
                endpoint=actual_endpoint,
                max_retries=max_retries,
                args=args,
                kwargs=kwargs,
            )

        return wrapper

    return decorator
