from __future__ import annotations


class HistoryLog:
    def __init__(self) -> None:
        self._items: list[tuple[str, str]] = []

    def add(self, key: str, value: str) -> None:
        self._items.append((key, value))

    def entries(self) -> tuple[tuple[str, str], ...]:
        return tuple(self._items)

    def tail(self, n: int) -> list[tuple[str, str]]:
        if n <= 0:
            return []
        return self._items[-n:]

    def to_dict(self) -> dict[str, list[str]]:
        grouped: dict[str, list[str]] = {}
        for key, value in self._items:
            grouped.setdefault(key, []).append(value)
        return grouped
