"""In-memory session store. One process, one dict — fine for local use."""
from __future__ import annotations

import uuid
from typing import Any

from .models import OutputMode, ProviderConfig

_SESSIONS: dict[str, dict[str, Any]] = {}


def new_session(topic: str, mode: OutputMode, provider: ProviderConfig) -> str:
    sid = uuid.uuid4().hex
    _SESSIONS[sid] = {
        "topic": topic,
        "mode": mode,
        "provider": provider.model_dump(),
        "history": [],
        "sources": [],
        "raw": "",
        "result": "",
    }
    return sid


def get(sid: str) -> dict[str, Any] | None:
    return _SESSIONS.get(sid)


def update(sid: str, **fields: Any) -> None:
    if sid in _SESSIONS:
        _SESSIONS[sid].update(fields)


def all_ids() -> list[str]:
    return list(_SESSIONS.keys())
