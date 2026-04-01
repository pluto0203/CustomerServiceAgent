from __future__ import annotations

from .history import HistoryLog
from .manager import MemoryManager
from .session_store import load_session, save_session
from .transcript import TranscriptStore


class SessionStore:
    save_session = staticmethod(save_session)
    load_session = staticmethod(load_session)


__all__ = [
    "TranscriptStore",
    "SessionStore",
    "HistoryLog",
    "MemoryManager",
]
