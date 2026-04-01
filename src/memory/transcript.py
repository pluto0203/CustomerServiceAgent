from __future__ import annotations


class TranscriptStore:
    def __init__(self) -> None:
        self.entries: list[str] = []
        self.flushed: bool = False

    def append(self, entry: str) -> None:
        self.entries.append(entry)
        self.flushed = False

    def compact(self, keep_last: int) -> None:
        if keep_last < 0:
            raise ValueError("keep_last must be >= 0")
        if keep_last == 0:
            self.entries = []
        elif len(self.entries) > keep_last:
            self.entries[:] = self.entries[-keep_last:]
            
    def replay(self) -> tuple[str, ...]:
        return tuple(self.entries)

    def flush(self) -> None:
        self.flushed = True

    def __len__(self) -> int:
        return len(self.entries)

    def __repr__(self) -> str:
        return f"TranscriptStore(len={len(self.entries)}, flushed={self.flushed})"
