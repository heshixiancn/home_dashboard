import time
from typing import Any

from .config import get_settings


class TTLCache:
    def __init__(self, ttl_seconds: int) -> None:
        self.ttl_seconds = ttl_seconds
        self._items: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        item = self._items.get(key)
        if not item:
            return None
        expires_at, value = item
        if expires_at < time.monotonic():
            self._items.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        self._items[key] = (time.monotonic() + self.ttl_seconds, value)

    def invalidate(self, prefix: str | None = None) -> None:
        if prefix is None:
            self._items.clear()
            return
        for key in list(self._items):
            if key.startswith(prefix):
                self._items.pop(key, None)


cache = TTLCache(ttl_seconds=get_settings().cache_ttl_seconds)
