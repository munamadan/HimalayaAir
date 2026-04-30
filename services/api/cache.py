from __future__ import annotations

import asyncio
from dataclasses import dataclass
from time import monotonic
from typing import Generic, TypeVar


ValueT = TypeVar("ValueT")


@dataclass(frozen=True)
class CacheEntry(Generic[ValueT]):
    value: ValueT
    expires_at: float


class TTLCache(Generic[ValueT]):
    def __init__(self, ttl_seconds: float) -> None:
        self.ttl_seconds = ttl_seconds
        self._items: dict[str, CacheEntry[ValueT]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> ValueT | None:
        async with self._lock:
            entry = self._items.get(key)
            if entry is None:
                return None
            if entry.expires_at <= monotonic():
                self._items.pop(key, None)
                return None
            return entry.value

    async def set(self, key: str, value: ValueT) -> None:
        async with self._lock:
            self._items[key] = CacheEntry(value=value, expires_at=monotonic() + self.ttl_seconds)

    async def clear(self) -> None:
        async with self._lock:
            self._items.clear()


@dataclass(frozen=True)
class ApiCaches:
    station_snapshots: TTLCache[object]
    idw: TTLCache[object]

    @classmethod
    def build(cls, *, station_ttl_seconds: float, idw_ttl_seconds: float) -> "ApiCaches":
        return cls(
            station_snapshots=TTLCache(ttl_seconds=station_ttl_seconds),
            idw=TTLCache(ttl_seconds=idw_ttl_seconds),
        )
