"""Research session endpoints.

Flow:
  1. POST /api/research        — create a session, seed history, return id
  2. GET  /api/research/{id}/stream — SSE stream of chunks, tool calls, final
  3. POST /api/research/{id}/followup — push another user turn into the session
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

log = logging.getLogger("research_assistant.research")

from .. import sessions
from ..agents.runner import SYSTEM_PROMPT, run_agent
from ..agents.synthesizer import format_sources_block, synthesize
from ..models import (
    FollowUpRequest,
    OutputMode,
    ProviderConfig,
    ResearchRequest,
    StartResponse,
)

router = APIRouter(prefix="/api/research", tags=["research"])


def _user_prompt(topic: str, mode: OutputMode) -> str:
    return (
        f"Research topic: {topic}\n\n"
        "Use web_search as needed to gather current information from multiple "
        "angles before writing your answer. When you have enough material, "
        "write a thorough Markdown answer with inline [n] citations matching "
        "the order in which sources were returned by the tool."
    )


@router.post("", response_model=StartResponse)
async def start_research(req: ResearchRequest) -> StartResponse:
    sid = sessions.new_session(req.topic, req.output_mode, req.provider)
    sess = sessions.get(sid)
    assert sess is not None
    sess["history"] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": _user_prompt(req.topic, req.output_mode)},
    ]
    log.info("session.start sid=%s mode=%s topic=%r", sid, req.output_mode, req.topic[:120])
    return StartResponse(session_id=sid)


@router.get("/{sid}/stream")
async def stream_research(sid: str) -> EventSourceResponse:
    sess = sessions.get(sid)
    if sess is None:
        raise HTTPException(404, "session not found")

    provider = ProviderConfig(**sess["provider"])
    mode: OutputMode = sess["mode"]
    log.info("session.stream sid=%s mode=%s", sid, mode)

    async def event_generator():
        raw_parts: list[str] = []
        async for event in run_agent(sess["history"], sess["sources"], provider):
            if event["type"] == "chunk":
                raw_parts.append(event["text"])
            yield {"event": "message", "data": json.dumps(event)}
            if event["type"] == "done":
                raw = "".join(raw_parts).strip()
                sess["raw"] = raw
                log.info("session.synthesize sid=%s raw_chars=%d sources=%d mode=%s", sid, len(raw), len(sess["sources"]), mode)
                if not raw:
                    log.warning("session.empty_raw sid=%s — skipping synthesizer", sid)
                    final = (
                        "_The model finished without producing any answer text. This often "
                        "happens with smaller local models that struggle with tool-calling. "
                        "Try a larger or more capable model, or check the backend logs for "
                        "tool-call errors._\n"
                        f"{format_sources_block(sess['sources'])}"
                    )
                else:
                    try:
                        final = await synthesize(raw, mode, provider, sess["sources"])
                    except Exception as exc:
                        final = (
                            f"{raw}\n\n_(synthesis step failed: {exc})_\n"
                            f"{format_sources_block(sess['sources'])}"
                        )
                sess["result"] = final
                yield {
                    "event": "message",
                    "data": json.dumps({"type": "result", "content": final, "mode": mode}),
                }
                return
            if event["type"] == "error":
                return

    return EventSourceResponse(event_generator())


@router.post("/{sid}/followup", response_model=StartResponse)
async def followup(sid: str, req: FollowUpRequest) -> StartResponse:
    sess = sessions.get(sid)
    if sess is None:
        raise HTTPException(404, "session not found")
    sess["provider"] = req.provider.model_dump()
    if req.output_mode:
        sess["mode"] = req.output_mode
    sess["history"].append({"role": "user", "content": req.question})
    sess["raw"] = ""
    sess["result"] = ""
    log.info("session.followup sid=%s mode=%s question=%r", sid, sess["mode"], req.question[:120])
    return StartResponse(session_id=sid)


@router.get("/{sid}")
async def get_session(sid: str) -> dict:
    sess = sessions.get(sid)
    if sess is None:
        raise HTTPException(404, "session not found")
    return {
        "session_id": sid,
        "topic": sess["topic"],
        "mode": sess["mode"],
        "result": sess["result"],
        "sources": sess["sources"],
    }
