import functools
import logging
import asyncio

def log_exceptions(func):
    if asyncio.iscoroutinefunction(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception:
                logging.error(f"Exception in {func.__qualname__}", exc_info=True)
    else:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception:
                logging.error(f"Exception in {func.__qualname__}", exc_info=True)
    return wrapper
