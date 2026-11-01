"""
rate_limiter.py
Rate limiting abstraction for VMT Backend APIs.

Architectural Note:
------------------
The InMemoryRateLimiter is intended strictly for DEVELOPMENT & SINGLE-PROCESS deployments.
For multi-worker production environments, implement SharedRateLimiter (e.g. backed by Redis).
"""
from abc import ABC, abstractmethod
from typing import Callable
from fastapi import Request, HTTPException, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.config import settings

class RateLimiter(ABC):
    """Abstract base class for VMT API rate limiting."""
    @abstractmethod
    def check_rate_limit(self, request: Request, key: str, limit_count: int, period_seconds: int) -> None:
        pass


# SlowAPI limiter instance for FastAPI route integration
slowapi_limiter = Limiter(key_func=get_remote_address)


class InMemoryRateLimiter(RateLimiter):
    """
    In-memory rate limiter for single-process development environment.
    Note: Does NOT share rate limit state across multiple processes or instances.
    """
    def __init__(self):
        self._limiter = slowapi_limiter

    def check_rate_limit(self, request: Request, key: str, limit_count: int, period_seconds: int) -> None:
        # In-memory check performed by slowapi / route rate limiters
        pass


def get_rate_limiter() -> RateLimiter:
    return InMemoryRateLimiter()
