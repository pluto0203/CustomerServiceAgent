from __future__ import annotations

from pathlib import Path
from typing import Any

from .history import HistoryLog
from .models import MemoryConfig, StoredSession, TurnResult
from .session_store import load_session, save_session
from .transcript import TranscriptStore


class MemoryManager:
    def __init__(self, session_id: str, config: MemoryConfig = MemoryConfig()):
        self.session_id = session_id
        self.config = config
        self.transcript = TranscriptStore()
        self.history = HistoryLog()
        self._turn = 0
        self._input_tokens = 0
        self._output_tokens = 0

    @classmethod
    def from_saved_session(
        cls,
        session_id: str,
        config: MemoryConfig = MemoryConfig(),
    ) -> "MemoryManager":
        stored = load_session(session_id=session_id, sessions_dir=config.sessions_dir)
        manager = cls(session_id=stored.session_id, config=config)
        manager.transcript.entries = list(stored.messages)
        manager.transcript.flush()
        manager._input_tokens = stored.input_tokens
        manager._output_tokens = stored.output_tokens
        manager._turn = len(stored.messages) // 2
        return manager

    def submit_turn(
        self,
        prompt: str,
        response: str,
        tokens: int = 0,
        routed_to: str = "",
    ) -> TurnResult:
        self.transcript.append(prompt)
        self.transcript.append(response)

        self._turn += 1
        self._input_tokens += len(prompt.split())
        self._output_tokens += max(0, tokens)

        self.history.add("turn", f"turn={self._turn}, routed_to={routed_to}")

        if self._turn >= self.config.compact_after_turns:
            self._compact()

        return TurnResult(
            turn=self._turn,
            prompt=prompt,
            response=response,
            tokens_used=tokens,
            routed_to=routed_to,
        )

    def _compact(self) -> None:
        self.transcript.compact(self.config.keep_last_turns)
        self.history.add("compact", f"kept={self.config.keep_last_turns}")

    def flush_to_disk(self) -> Path:
        stored = StoredSession(
            session_id=self.session_id,
            messages=self.transcript.replay(),
            input_tokens=self._input_tokens,
            output_tokens=self._output_tokens,
        )
        saved_path = save_session(stored, self.config.sessions_dir)
        self.transcript.flush()
        self.history.add("flush", str(saved_path))
        return saved_path

    def snapshot(self) -> dict[str, Any]:
        total_tokens = self._input_tokens + self._output_tokens
        return {
            "session_id": self.session_id,
            "turn": self._turn,
            "transcript_len": len(self.transcript),
            "flushed": self.transcript.flushed,
            "total_tokens": total_tokens,
            "history_tail": self.history.tail(5),
        }
