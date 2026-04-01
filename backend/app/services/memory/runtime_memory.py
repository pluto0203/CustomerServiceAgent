from __future__ import annotations

import importlib
import logging
import sys
from pathlib import Path
from typing import Any

from app.core.config import settings


logger = logging.getLogger(__name__)


def _load_memory_types() -> tuple[type[Any], type[Any]] | None:
    try:
        memory_module = importlib.import_module("memory")
    except ModuleNotFoundError:
        repo_root = Path(__file__).resolve().parents[4]
        src_dir = repo_root / "src"
        if src_dir.exists() and str(src_dir) not in sys.path:
            sys.path.append(str(src_dir))
        try:
            memory_module = importlib.import_module("memory")
        except ModuleNotFoundError:
            logger.warning("memory package not found under src/. Runtime memory is disabled.")
            return None

    return getattr(memory_module, "MemoryConfig"), getattr(memory_module, "MemoryManager")


def create_or_restore_memory_manager(session_id: str) -> Any | None:
    if not settings.MEMORY_ENABLED:
        return None

    loaded = _load_memory_types()
    if loaded is None:
        return None

    memory_config_cls, memory_manager_cls = loaded
    config = memory_config_cls(
        compact_after_turns=settings.MEMORY_COMPACT_AFTER_TURNS,
        keep_last_turns=settings.MEMORY_KEEP_LAST_TURNS,
        sessions_dir=settings.MEMORY_SESSIONS_DIR,
    )

    try:
        return memory_manager_cls.from_saved_session(session_id=session_id, config=config)
    except FileNotFoundError:
        return memory_manager_cls(session_id=session_id, config=config)
