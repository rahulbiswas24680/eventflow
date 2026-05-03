"""
Caching utilities for EventFlow.
Provides view-level caching, low-level caching with stampede prevention, and cache invalidation.
"""

from django.core.cache import cache
from django.conf import settings
from functools import wraps
import hashlib
import json
import logging

logger = logging.getLogger(__name__)


def generate_cache_key(prefix, *args, **kwargs):
    """Generate a consistent cache key from prefix and arguments."""
    key_parts = [prefix]
    
    for arg in args:
        key_parts.append(str(arg))
    
    for key, value in sorted(kwargs.items()):
        key_parts.append(f"{key}:{value}")
    
    key_string = ":".join(key_parts)
    
    if len(key_string) > 200:
        hash_obj = hashlib.md5(key_string.encode())
        return f"{prefix}:{hash_obj.hexdigest()}"
    
    return key_string


def get_or_set_cache(key, callable_func, timeout=300, version=None):
    """
    Get value from cache or compute and store it.
    Simple version without stampede prevention.
    
    Args:
        key: Cache key
        callable_func: Function to call if cache misses
        timeout: Cache TTL in seconds (default 5 minutes)
        version: Cache version for invalidation
    """
    try:
        cached_value = cache.get(key, version=version)
        if cached_value is not None:
            return cached_value
        
        value = callable_func()
        cache.set(key, value, timeout=timeout, version=version)
        return value
    except Exception as e:
        logger.warning(f"Cache error for key {key}: {e}")
        return callable_func()


def get_or_set_cache_with_lock(key, callable_func, timeout=300, lock_timeout=10):
    """
    Get value from cache with stampede prevention using lock pattern.
    Uses cache.add() to implement locking - only one caller computes the value.
    
    Args:
        key: Cache key
        callable_func: Function to call if cache misses
        timeout: Cache TTL in seconds
        lock_timeout: How long to wait for lock release
    
    Returns:
        Cached or computed value
    """
    lock_key = f"{key}:lock"
    
    try:
        cached_value = cache.get(key)
        if cached_value is not None:
            return cached_value
        
        if cache.add(lock_key, "1", lock_timeout):
            try:
                value = callable_func()
                cache.set(key, value, timeout=timeout)
                return value
            finally:
                cache.delete(lock_key)
        else:
            import time
            for _ in range(lock_timeout * 2):
                time.sleep(0.5)
                cached_value = cache.get(key)
                if cached_value is not None:
                    return cached_value
            
            return callable_func()
    
    except Exception as e:
        logger.warning(f"Cache lock error for key {key}: {e}")
        return callable_func()


def invalidate_cache_keys(pattern):
    """
    Invalidate all cache keys matching a pattern.
    Note: This requires django-redis with pattern support.
    
    Args:
        pattern: Key pattern to match (e.g., "events:*")
    """
    try:
        from django_redis import get_redis_connection
        redis_client = get_redis_connection("default")
        keys = redis_client.keys(pattern)
        if keys:
            redis_client.delete(*keys)
            logger.info(f"Invalidated {len(keys)} cache keys matching {pattern}")
    except Exception as e:
        logger.warning(f"Failed to invalidate cache pattern {pattern}: {e}")


def invalidate_model_cache(model_name, instance_id=None):
    """
    Invalidate cache for a specific model.
    
    Args:
        model_name: Name of the model (e.g., "event", "tickettype")
        instance_id: Specific instance ID to invalidate, or None for all
    """
    if instance_id:
        key = f"{model_name}:{instance_id}"
        cache.delete(key)
    else:
        invalidate_cache_keys(f"{model_name}:*")


class CacheMixin:
    """Mixin class to add caching to views."""
    
    cache_timeout = 300  # 5 minutes default
    cache_version = 1
    
    def get_cache_key(self):
        """Generate cache key based on request."""
        return generate_cache_key(
            self.__class__.__name__,
            self.request.path,
            self.request.GET.dict()
        )
    
    def get_cache_timeout(self):
        return self.cache_timeout
    
    def get(self, request, *args, **kwargs):
        cache_key = self.get_cache_key()
        
        cached_response = cache.get(cache_key, version=self.cache_version)
        if cached_response:
            return cached_response
        
        response = super().get(request, *args, **kwargs)
        
        if response.status_code == 200:
            cache.set(
                cache_key,
                response,
                timeout=self.get_cache_timeout(),
                version=self.cache_version
            )
        
        return response


def cached_view(timeout=300, key_prefix="view"):
    """
    Decorator for caching view responses.
    
    Args:
        timeout: Cache TTL in seconds
        key_prefix: Prefix for cache key
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.method != 'GET':
                return view_func(request, *args, **kwargs)
            
            cache_key = generate_cache_key(
                key_prefix,
                request.path,
                request.GET.dict()
            )
            
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
            
            response = view_func(request, *args, **kwargs)
            
            if response.status_code == 200:
                cache.set(cache_key, response, timeout=timeout)
            
            return response
        
        return wrapper
    return decorator


def invalidate_cache_on_save(sender, instance, **kwargs):
    """
    Signal handler to invalidate cache on model save.
    Usage: 
        from django.db.models.signals import post_save
        post_save.connect(invalidate_cache_on_save, sender=Event)
    """
    model_name = sender._meta.model_name
    invalidate_model_cache(model_name, instance.pk)


def invalidate_cache_on_delete(sender, instance, **kwargs):
    """
    Signal handler to invalidate cache on model delete.
    Usage:
        from django.db.models.signals import post_delete
        post_delete.connect(invalidate_cache_on_delete, sender=Event)
    """
    model_name = sender._meta.model_name
    invalidate_model_cache(model_name, instance.pk)