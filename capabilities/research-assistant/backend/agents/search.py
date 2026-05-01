"""Web search via the DuckDuckGo SERP (no API key required).

Uses the `ddgs` library to scrape DuckDuckGo's HTML results page. The
library is sync, so we run it in a thread.
"""
from __future__ import annotations

import asyncio
import logging

log = logging.getLogger("research_assistant.search")


async def web_search(query: str, max_results: int = 6) -> list[dict[str, str]]:
    try:
        from ddgs import DDGS
    except ImportError:
        log.warning("search — `ddgs` package not installed")
        return []

    log.info("search.start query=%r", query)

    def _run() -> list[dict[str, str]]:
        out: list[dict[str, str]] = []
        with DDGS() as client:
            for r in client.text(query, max_results=max_results):
                out.append({
                    "title": r.get("title", "") or "",
                    "url": r.get("href", "") or r.get("url", "") or "",
                    "snippet": r.get("body", "") or "",
                })
        return out

    try:
        results = await asyncio.to_thread(_run)
    except Exception as exc:
        log.warning("search.fail query=%r error=%s", query, exc)
        return []
    log.info("search.ok query=%r results=%d", query, len(results))
    return results
