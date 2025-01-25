from pymemcache.client.hash import HashClient
from pymemcache.client.base import PooledClient, Client
from functools import wraps
import asyncio
import json
import logging
from typing import Any, Optional
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class CacheConfig:
    TIMEOUT = 1.0  # seconds
    MAX_POOL_SIZE = 10
    SERVER_LIST = [('127.0.0.1', 11211)]
    CIRCUIT_BREAKER_FAILURES = 5
    CIRCUIT_BREAKER_RESET_TIME = 60  # seconds

class AsyncCache:
    def __init__(self):
        self._client = PooledClient(
            CacheConfig.SERVER_LIST[0],
            connect_timeout=CacheConfig.TIMEOUT,
            timeout=CacheConfig.TIMEOUT,
            max_pool_size=CacheConfig.MAX_POOL_SIZE
        )
        self._executor = ThreadPoolExecutor(max_workers=CacheConfig.MAX_POOL_SIZE)
        self._failure_count = 0
        self._circuit_open = False
        self._last_failure_time = 0

    async def get(self, key: str, default: Any = None) -> Optional[Any]:
        if self._circuit_open:
            logger.warning("Circuit breaker open - skipping cache")
            return default
        
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                self._executor,
                self._safe_get,
                key
            )
            self._failure_count = 0
            return result
        except Exception as e:
            self._handle_failure(e)
            return default

    async def set(self, key: str, value: Any, expire: int = 0) -> bool:
        if self._circuit_open:
            return False
            
        try:
            return await asyncio.get_event_loop().run_in_executor(
                self._executor,
                self._safe_set,
                key,
                value,
                expire
            )
        except Exception as e:
            self._handle_failure(e)
            return False

    async def delete(self, key: str) -> bool:
        """Delete a key from cache asynchronously."""
        if self._circuit_open:
            return False
            
        try:
            return await asyncio.get_event_loop().run_in_executor(
                self._executor,
                self._safe_delete,
                key
            )
        except Exception as e:
            self._handle_failure(e)
            return False

    def _safe_get(self, key: str) -> Optional[Any]:
        try:
            result = self._client.get(key)
            return result.decode('utf-8') if result else None
        except Exception as e:
            logger.error(f"Cache get error: {str(e)}")
            raise

    def _safe_set(self, key: str, value: Any, expire: int = 0) -> bool:
        try:
            return bool(self._client.set(key, value, expire=expire))
        except Exception as e:
            logger.error(f"Cache set error: {str(e)}")
            raise

    def _safe_delete(self, key: str) -> bool:
        """Safely execute delete operation."""
        try:
            return bool(self._client.delete(key))
        except Exception as e:
            logger.error(f"Cache delete error: {str(e)}")
            raise

    def _handle_failure(self, error: Exception):
        self._failure_count += 1
        logger.error(f"Cache operation failed: {str(error)}")
        
        if self._failure_count >= CacheConfig.CIRCUIT_BREAKER_FAILURES:
            self._circuit_open = True
            self._last_failure_time = asyncio.get_event_loop().time()
            logger.warning("Circuit breaker opened")

    async def cleanup(self):
        self._executor.shutdown(wait=True)
        self._client.close()

cache_client = AsyncCache()