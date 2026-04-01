"""
Telegram Callback Query Deduplication Service.

Prevents double-processing of callback button clicks using in-memory cache.
For production with multiple workers, replace with Redis implementation.
"""

import time
from threading import Lock
from typing import Dict

from app.logging_config import get_logger

logger = get_logger("callback_dedup")

# In-memory cache with TTL
_processed_callbacks: Dict[str, float] = {}
_cache_lock = Lock()
_CALLBACK_TTL_SECONDS = 60  # Keep callback IDs for 60 seconds


def _cleanup_expired() -> int:
    """Remove expired entries from cache. Returns count of removed entries."""
    now = time.time()
    expired = [k for k, v in _processed_callbacks.items() if now - v > _CALLBACK_TTL_SECONDS]
    for k in expired:
        del _processed_callbacks[k]
    return len(expired)


def is_callback_processed(callback_id: str) -> bool:
    """
    Check if callback was already processed.
    
    Returns True if this callback_id was seen before (duplicate).
    Returns False if this is the first time seeing this callback_id.
    
    Thread-safe implementation using lock.
    """
    if not callback_id:
        return False
    
    now = time.time()
    
    with _cache_lock:
        # Periodic cleanup (every 100 calls or so)
        if len(_processed_callbacks) > 1000:
            _cleanup_expired()
        
        # Check if already processed
        if callback_id in _processed_callbacks:
            expiry = _processed_callbacks[callback_id]
            if now - expiry < _CALLBACK_TTL_SECONDS:
                logger.debug(f"Duplicate callback detected: {callback_id}")
                return True
            # Expired, remove and continue
            del _processed_callbacks[callback_id]
        
        # Mark as processed
        _processed_callbacks[callback_id] = now
        return False


def clear_cache() -> int:
    """Clear all cached callbacks. Returns count of cleared entries."""
    with _cache_lock:
        count = len(_processed_callbacks)
        _processed_callbacks.clear()
        return count
