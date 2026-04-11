"""Exponential backoff retry decorator for Gemini LLM and Supabase RPC calls.

Wraps callable functions so that transient API errors (rate-limits, server
overloads, connection resets) are retried with jittered exponential delay
instead of propagating immediately.

Jitter is added to each delay to prevent thundering-herd on shared rate limits
when multiple tools fire simultaneously.
"""

from __future__ import annotations

import logging
import random
import time
from functools import wraps
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])

# ── Retryable exception classes (initialised lazily to avoid import overhead) ─
_RETRYABLE_EXCEPTION_CLASSES: tuple[type[Exception], ...] | None = None


def _get_retryable_exceptions() -> tuple[type[Exception], ...]:
    """Lazily import exception classes that qualify for automatic retry.

    Returns:
        Tuple of exception classes considered retryable.
    """
    global _RETRYABLE_EXCEPTION_CLASSES
    if _RETRYABLE_EXCEPTION_CLASSES is not None:
        return _RETRYABLE_EXCEPTION_CLASSES

    classes: list[type[Exception]] = []

    try:
        from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable

        classes.extend([ResourceExhausted, ServiceUnavailable])
    except ImportError:
        pass

    try:
        from httpx import HTTPStatusError, ConnectError, ReadTimeout

        classes.extend([HTTPStatusError, ConnectError, ReadTimeout])
    except ImportError:
        pass

    _RETRYABLE_EXCEPTION_CLASSES = tuple(classes)
    return _RETRYABLE_EXCEPTION_CLASSES


def _is_retryable(exc: Exception) -> bool:
    """Determine whether an exception qualifies for automatic retry.

    An exception is retryable if it is one of the known retryable classes
    **or** if its string representation contains markers for HTTP 429/5xx,
    quota exhaustion, or rate limiting.

    Args:
        exc: The caught exception instance.

    Returns:
        ``True`` if the call should be retried, ``False`` otherwise.
    """
    # Prefer typed exception matching for accuracy
    for cls in _get_retryable_exceptions():
        if isinstance(exc, cls):
            return True

    # Fall back to string-based heuristics for unknown exception types
    error_str = str(exc).lower()

    is_rate_limit = "429" in error_str or "rate limit" in error_str
    is_quota = "resource_exhausted" in error_str or "quota exceeded" in error_str
    is_server_error = any(code in error_str for code in ("500", "502", "503", "504"))
    is_network = "upstream connect" in error_str or "connection" in error_str

    return is_rate_limit or is_quota or is_server_error or is_network


def exponential_backoff(
    max_retries: int = 3,
    base_delay_seconds: float = 2.0,
    backoff_multiplier: float = 2.0,
    jitter_factor: float = 0.25,
) -> Callable[[F], F]:
    """Decorator that retries a function with jittered exponential backoff.

    On a retryable error, the function waits::

        delay = base_delay_seconds * backoff_multiplier^attempt
                * uniform(1 - jitter_factor, 1 + jitter_factor)

    Non-retryable exceptions are re-raised immediately without waiting.

    Args:
        max_retries: Maximum retry attempts before the final exception is raised.
        base_delay_seconds: Initial wait time in seconds before the first retry.
        backoff_multiplier: Multiplicative factor applied to delay after each retry.
        jitter_factor: Fraction of the delay added as random jitter (0 = no jitter).

    Returns:
        Decorated function with retry logic applied, preserving the original
        function signature and docstring.
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            delay = base_delay_seconds
            last_exception: Exception

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)

                except Exception as exc:
                    last_exception = exc

                    if not _is_retryable(exc):
                        raise  # non-retryable — bubble up immediately

                    if attempt < max_retries:
                        jitter = random.uniform(1 - jitter_factor, 1 + jitter_factor)
                        sleep_time = delay * jitter
                        logger.warning(
                            "Attempt %d/%d failed (%s: %s). Retrying in %.2fs…",
                            attempt + 1,
                            max_retries,
                            type(exc).__name__,
                            str(exc)[:200],
                            sleep_time,
                        )
                        time.sleep(sleep_time)
                        delay *= backoff_multiplier
                    else:
                        logger.error(
                            "All %d attempt(s) exhausted. Last error: %s: %s",
                            max_retries + 1,
                            type(last_exception).__name__,
                            last_exception,
                        )

            raise last_exception  # type: ignore[possibly-undefined]

        return wrapper  # type: ignore[return-value]

    return decorator
