"""Exponential backoff retry decorator for tool execution.

Wraps tool ``_run`` methods so that transient API errors (rate-limits,
server overloads, connection resets) are retried with exponential delay
instead of crashing the pipeline.
"""

from __future__ import annotations

import logging
import time
from functools import wraps
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)
F = TypeVar("F", bound=Callable[..., Any])


def with_exponential_backoff(
    max_retries: int = 3,
    base_delay_seconds: float = 1.0,
    backoff_multiplier: float = 2.0,
) -> Callable[[F], F]:
    """Decorator that retries a function with exponential backoff on transient errors.

    Args:
        max_retries: Maximum number of retry attempts before raising.
        base_delay_seconds: Initial wait time before the first retry.
        backoff_multiplier: Factor by which delay grows on each retry.

    Returns:
        Decorated function with retry logic applied.
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            delay = base_delay_seconds
            last_exception: Exception | None = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    last_exception = exc
                    error_str = str(exc).lower()

                    # Check if this is a retryable error
                    is_rate_limit = "429" in error_str or "rate limit" in error_str
                    is_server_error = any(
                        code in error_str
                        for code in ("500", "502", "503", "504")
                    )
                    is_overflow = (
                        "overflow" in error_str
                        or "upstream connect" in error_str
                    )

                    if not (is_rate_limit or is_server_error or is_overflow):
                        raise  # non-retryable — bubble up immediately

                    if attempt < max_retries:
                        logger.warning(
                            "Attempt %d/%d failed (%s). Retrying in %.1fs...",
                            attempt + 1,
                            max_retries,
                            type(exc).__name__,
                            delay,
                        )
                        time.sleep(delay)
                        delay *= backoff_multiplier
                    else:
                        logger.error(
                            "All %d attempts failed. Last error: %s",
                            max_retries,
                            exc,
                        )

            raise last_exception  # type: ignore[misc]

        return wrapper  # type: ignore[return-value]

    return decorator
