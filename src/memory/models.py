from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MemoryConfig:
    compact_after_turns: int = 10
    keep_last_turns: int = 6
    sessions_dir: str = ".agent_sessions"


@dataclass(frozen=True)
class StoredSession:
    session_id: str
    messages: tuple[str, ...]
    input_tokens: int
    output_tokens: int


@dataclass
class TurnResult:
    turn: int
    prompt: str
    response: str
    tokens_used: int
    routed_to: str
