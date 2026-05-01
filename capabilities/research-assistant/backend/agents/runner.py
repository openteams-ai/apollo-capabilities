"""Agentic loop using any OpenAI-compatible endpoint.

A new AsyncOpenAI client is instantiated per request so each session can target
a different base URL / API key / model. Streaming chunks, tool-call notices,
and a final 'done' event are yielded so a router can forward them as SSE.
"""
from __future__ import annotations

import json
import logging
import time
from collections.abc import AsyncIterator
from typing import Any

from openai import AsyncOpenAI

from ..models import ProviderConfig
from .search import web_search

log = logging.getLogger("research_assistant.runner")

SYSTEM_PROMPT = (
    "You are a careful research assistant. Use the web_search tool to gather "
    "current, factual information. Prefer multiple searches across different "
    "angles of the topic. After gathering enough material, write a clear, "
    "well-organized answer in Markdown. Cite sources inline as [n] where n "
    "matches the order they were returned to you. Never fabricate URLs or facts."
)

WEB_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "Search the web for current information on a topic. Returns a list of {title, url, snippet} results.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
            },
            "required": ["query"],
        },
    },
}


def make_client(provider: ProviderConfig) -> AsyncOpenAI:
    return AsyncOpenAI(
        base_url=provider.base_url,
        api_key=provider.api_key or "not-needed",
    )


async def run_agent(
    history: list[dict[str, Any]],
    sources: list[dict[str, str]],
    provider: ProviderConfig,
    max_iterations: int = 6,
) -> AsyncIterator[dict[str, Any]]:
    """Drive the model/tool loop, yielding SSE-style events as we go.

    `history` and `sources` are mutated in place so the caller can persist
    the updated session state once iteration ends.
    """
    client = make_client(provider)
    log.info(
        "agent.start model=%s base_url=%s history_len=%d existing_sources=%d max_iter=%d",
        provider.model, provider.base_url, len(history), len(sources), max_iterations,
    )

    all_text_parts: list[str] = []
    last_iteration = 0
    exit_reason = "max_iter"

    for iteration in range(1, max_iterations + 1):
        last_iteration = iteration
        log.info("agent.iter %d/%d — calling LLM (messages=%d)", iteration, max_iterations, len(history))
        t0 = time.monotonic()
        try:
            stream = await client.chat.completions.create(
                model=provider.model,
                messages=history,
                tools=[WEB_SEARCH_TOOL],
                stream=True,
            )
        except Exception as exc:
            log.exception("agent.iter %d — LLM call failed", iteration)
            yield {"type": "error", "message": f"LLM call failed: {exc}"}
            return

        text_parts: list[str] = []
        tool_calls: dict[int, dict[str, Any]] = {}
        finish_reason: str | None = None
        chunk_count = 0

        async for chunk in stream:
            if not chunk.choices:
                continue
            choice = chunk.choices[0]
            delta = choice.delta

            if delta and delta.content:
                text_parts.append(delta.content)
                all_text_parts.append(delta.content)
                chunk_count += 1
                yield {"type": "chunk", "text": delta.content}

            if delta and delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    bucket = tool_calls.setdefault(
                        idx,
                        {"id": "", "type": "function", "function": {"name": "", "arguments": ""}},
                    )
                    if tc.id:
                        bucket["id"] = tc.id
                    if tc.function:
                        if tc.function.name:
                            bucket["function"]["name"] = tc.function.name
                        if tc.function.arguments:
                            bucket["function"]["arguments"] += tc.function.arguments

            if choice.finish_reason:
                finish_reason = choice.finish_reason

        elapsed = time.monotonic() - t0
        text_len = sum(len(p) for p in text_parts)
        log.info(
            "agent.iter %d — finish=%s chunks=%d text_chars=%d tool_calls=%d elapsed=%.2fs",
            iteration, finish_reason, chunk_count, text_len, len(tool_calls), elapsed,
        )

        assistant_msg: dict[str, Any] = {"role": "assistant", "content": "".join(text_parts) or None}
        if tool_calls:
            assistant_msg["tool_calls"] = [tool_calls[i] for i in sorted(tool_calls)]
        history.append(assistant_msg)

        if finish_reason == "tool_calls" and tool_calls:
            for tc in assistant_msg["tool_calls"]:
                name = tc["function"]["name"]
                raw_args = tc["function"].get("arguments") or "{}"
                try:
                    args = json.loads(raw_args)
                except json.JSONDecodeError:
                    log.warning("agent.tool — bad JSON arguments for %s: %r", name, raw_args)
                    args = {}
                if name == "web_search":
                    query = (args.get("query") or "").strip()
                    log.info("agent.tool web_search query=%r", query)
                    yield {"type": "tool_call", "name": name, "query": query}
                    s0 = time.monotonic()
                    try:
                        results = await web_search(query) if query else []
                    except Exception as exc:
                        log.exception("agent.tool web_search failed query=%r", query)
                        results = []
                        yield {"type": "tool_error", "name": name, "message": str(exc)}
                    new_count = 0
                    for r in results:
                        if r["url"] and not any(s["url"] == r["url"] for s in sources):
                            sources.append(r)
                            new_count += 1
                    log.info(
                        "agent.tool web_search results=%d new=%d total_sources=%d elapsed=%.2fs",
                        len(results), new_count, len(sources), time.monotonic() - s0,
                    )
                    history.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": json.dumps(results),
                    })
                else:
                    log.warning("agent.tool unknown name=%r", name)
                    history.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": json.dumps({"error": f"unknown tool {name}"}),
                    })
            continue

        exit_reason = "stop"
        break
    else:
        exit_reason = "max_iter"
        log.warning("agent.max_iter_reached iter=%d sources=%d", max_iterations, len(sources))

    accumulated = "".join(all_text_parts).strip()
    has_tool_results = any(msg.get("role") == "tool" for msg in history)
    needs_forced_final = (not accumulated) or exit_reason == "max_iter"
    if needs_forced_final and has_tool_results:
        if sources:
            instruction = (
                "Now write your final research answer using the search results above. "
                "Use Markdown with inline [n] citations to the sources you found. "
                "Do not call any more tools."
            )
        else:
            instruction = (
                "The web_search tool returned no results for any of your queries. "
                "Do not call any more tools. Write a brief Markdown answer that "
                "honestly states no current sources were found, summarizes what is "
                "generally known about the topic from your training, and clearly "
                "labels that material as background (no citations)."
            )
        log.warning(
            "agent.force_final exit=%s sources=%d stripped_text=%d — running closing turn",
            exit_reason, len(sources), len(accumulated),
        )
        history.append({"role": "user", "content": instruction})
        try:
            forced = await client.chat.completions.create(
                model=provider.model,
                messages=history,
                stream=True,
            )
            forced_parts: list[str] = []
            async for chunk in forced:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    forced_parts.append(delta.content)
                    all_text_parts.append(delta.content)
                    yield {"type": "chunk", "text": delta.content}
            if forced_parts:
                history.append({"role": "assistant", "content": "".join(forced_parts)})
            log.info("agent.force_final produced text_chars=%d", sum(len(p) for p in forced_parts))
        except Exception as exc:
            log.exception("agent.force_final failed")
            yield {"type": "error", "message": f"final-answer call failed: {exc}"}
            return

    final_stripped = len("".join(all_text_parts).strip())
    log.info(
        "agent.done exit=%s iter=%d total_text=%d total_sources=%d",
        exit_reason, last_iteration, final_stripped, len(sources),
    )
    yield {"type": "done", "sources": sources}
