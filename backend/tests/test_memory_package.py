from __future__ import annotations

from pathlib import Path

from memory import MemoryConfig, MemoryManager


def test_memory_manager_flush_and_restore(tmp_path: Path) -> None:
    sessions_dir = tmp_path / "sessions"
    manager = MemoryManager(
        session_id="session-1",
        config=MemoryConfig(
            compact_after_turns=10,
            keep_last_turns=6,
            sessions_dir=str(sessions_dir),
        ),
    )

    manager.submit_turn("hello", "world", tokens=12, routed_to="unit-test")
    saved_path = manager.flush_to_disk()

    assert saved_path.exists()
    assert saved_path.name == "session-1.json"

    restored = MemoryManager.from_saved_session(
        "session-1",
        config=MemoryConfig(sessions_dir=str(sessions_dir)),
    )
    snap = restored.snapshot()

    assert snap["session_id"] == "session-1"
    assert snap["transcript_len"] == 2
    assert snap["flushed"] is True
