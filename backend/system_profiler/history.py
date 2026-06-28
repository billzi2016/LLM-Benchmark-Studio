from __future__ import annotations

from collections import deque
from copy import deepcopy
from threading import Lock
from typing import Any


class MetricsHistory:
    def __init__(self, maxlen: int = 300) -> None:
        self._items: deque[dict[str, Any]] = deque(maxlen=maxlen)
        self._lock = Lock()

    def append(self, snapshot: dict[str, Any]) -> None:
        with self._lock:
            self._items.append(deepcopy(snapshot))

    def latest(self) -> dict[str, Any] | None:
        with self._lock:
            if not self._items:
                return None
            return deepcopy(self._items[-1])

    def list(self) -> list[dict[str, Any]]:
        with self._lock:
            return [deepcopy(item) for item in self._items]
