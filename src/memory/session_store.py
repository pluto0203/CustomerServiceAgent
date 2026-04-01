from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .models import StoredSession


def save_session(session: StoredSession, sessions_dir: str) -> Path:
    directory = Path(sessions_dir)
    directory.mkdir(parents=True, exist_ok=True)

    output_path = directory / f"{session.session_id}.json"
    payload = asdict(session)
    payload["messages"] = list(session.messages)

    output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return output_path


def load_session(session_id: str, sessions_dir: str) -> StoredSession:
    input_path = Path(sessions_dir) / f"{session_id}.json"
    if not input_path.exists():
        raise FileNotFoundError(
            f"Session file not found for session_id='{session_id}' at '{input_path}'"
        )

    raw = json.loads(input_path.read_text(encoding="utf-8"))
    return StoredSession(
        session_id=str(raw["session_id"]),
        messages=tuple(raw.get("messages", [])),
        input_tokens=int(raw.get("input_tokens", 0)),
        output_tokens=int(raw.get("output_tokens", 0)),
    )
