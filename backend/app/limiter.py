"""
Shared application rate limiter.

Uses in-memory storage by default — fine for a single instance and local dev.
Set RATELIMIT_STORAGE_URI to a Redis URL in production so the rate-limit
counters are shared across every backend instance behind the load balancer
(otherwise each instance counts independently and the real limit is N×).
"""
import os

from slowapi import Limiter
from slowapi.util import get_remote_address

_storage_uri = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")

limiter = Limiter(key_func=get_remote_address, storage_uri=_storage_uri)
