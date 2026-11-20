"""Small, process-local cache for serialized dataset profiles.

The cache never stores DataFrames. Authorization must be completed by the
caller before ``get`` or ``put`` is used.
"""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
import sys
from threading import RLock
import time

from .models import DatasetProfile


PROFILE_VERSION = "3.0"


@dataclass(frozen=True, slots=True)
class ProfileCacheKey:
    owner_id: str
    dataset_id: str
    profile_version: str
    file_size: int
    file_mtime_ns: int


@dataclass(slots=True)
class _Entry:
    payload: str
    expires_at: float
    size_bytes: int


class ProfileCache:
    def __init__(self, ttl_seconds: int, max_entries: int, max_bytes: int):
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self.max_bytes = max_bytes
        self._entries: OrderedDict[ProfileCacheKey, _Entry] = OrderedDict()
        self._bytes = 0
        self._lock = RLock()

    @property
    def entry_count(self) -> int:
        with self._lock:
            self._remove_expired(time.monotonic())
            return len(self._entries)

    @property
    def current_bytes(self) -> int:
        with self._lock:
            self._remove_expired(time.monotonic())
            return self._bytes

    def get(self, key: ProfileCacheKey) -> DatasetProfile | None:
        now = time.monotonic()
        with self._lock:
            self._remove_expired(now)
            entry = self._entries.get(key)
            if entry is None:
                return None
            self._entries.move_to_end(key)
            payload = entry.payload
        return DatasetProfile.model_validate_json(payload)

    def put(self, key: ProfileCacheKey, profile: DatasetProfile) -> None:
        payload = profile.model_dump_json()
        # The payload is the dominant retained object. Include key and entry
        # overhead so the configured budget is not merely a payload-length cap.
        size_bytes = (
            sys.getsizeof(payload)
            + sys.getsizeof(key)
            + sys.getsizeof(key.owner_id)
            + sys.getsizeof(key.dataset_id)
            + sys.getsizeof(key.profile_version)
            + sys.getsizeof(_Entry)
            + 256  # conservative OrderedDict/node and integer-field overhead
        )
        if size_bytes > self.max_bytes:
            return
        now = time.monotonic()
        with self._lock:
            self._remove_expired(now)
            self._remove_matching(key.owner_id, key.dataset_id)
            self._entries[key] = _Entry(payload, now + self.ttl_seconds, size_bytes)
            self._bytes += size_bytes
            while len(self._entries) > self.max_entries or self._bytes > self.max_bytes:
                self._pop_oldest()

    def invalidate(self, owner_id: str, dataset_id: str) -> None:
        with self._lock:
            self._remove_matching(owner_id, dataset_id)

    def _remove_expired(self, now: float) -> None:
        for key, entry in list(self._entries.items()):
            if entry.expires_at <= now:
                self._remove(key)

    def _remove_matching(self, owner_id: str, dataset_id: str) -> None:
        for key in list(self._entries):
            if key.owner_id == owner_id and key.dataset_id == dataset_id:
                self._remove(key)

    def _pop_oldest(self) -> None:
        _key, entry = self._entries.popitem(last=False)
        self._bytes -= entry.size_bytes

    def _remove(self, key: ProfileCacheKey) -> None:
        entry = self._entries.pop(key, None)
        if entry is not None:
            self._bytes -= entry.size_bytes
