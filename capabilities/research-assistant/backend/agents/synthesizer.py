"""Reformat raw research output into a requested output mode.

Uses the same OpenAI-compatible provider configured on the request — no
streaming, single completion call per synthesis.
"""
from __future__ import annotations

import logging
import time

from ..models import OutputMode, ProviderConfig
from .runner import make_client

log = logging.getLogger("research_assistant.synthesizer")

MODE_INSTRUCTIONS: dict[OutputMode, str] = {
    "summary": (
        "Reformat the research below as a TL;DR paragraph followed by exactly "
        "5 key bullet points. Keep inline [n] citations intact."
    ),
    "report": (
        "Reformat the research below as a structured report with H2 headings "
        "(##) for each major section and inline [n] citations. Start with a "
        "short executive summary."
    ),
    "pros_cons": (
        "Reformat the research below as a markdown table with two columns: "
        "Pros and Cons. Each row should be a single concise point. Keep "
        "inline [n] citations on the relevant items."
    ),
    "timeline": (
        "Reformat the research below as a chronological bulleted list. Bold "
        "every date or year (e.g. **2024-03**: ...). Keep inline [n] citations."
    ),
    "open_questions": (
        "List the most important unanswered questions, gaps, and uncertainties "
        "raised by the research below as a numbered list. For each question, "
        "briefly note why it matters."
    ),
}


def format_sources_block(sources: list[dict]) -> str:
    if not sources:
        return ""
    lines = ["", "## Sources", ""]
    for i, s in enumerate(sources, start=1):
        title = s.get("title") or s.get("url") or f"Source {i}"
        url = s.get("url") or ""
        lines.append(f"{i}. [{title}]({url})")
    return "\n".join(lines)


async def synthesize(
    raw: str,
    mode: OutputMode,
    provider: ProviderConfig,
    sources: list[dict],
) -> str:
    instruction = MODE_INSTRUCTIONS[mode]
    client = make_client(provider)
    log.info("synthesize.start mode=%s raw_chars=%d sources=%d", mode, len(raw), len(sources))
    t0 = time.monotonic()
    resp = await client.chat.completions.create(
        model=provider.model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You reformat research into specific output modes. Do not "
                    "invent new facts. Preserve every [n] citation."
                ),
            },
            {
                "role": "user",
                "content": f"{instruction}\n\n---\n\n{raw}",
            },
        ],
        stream=False,
    )
    body = (resp.choices[0].message.content or "").strip()
    log.info("synthesize.done mode=%s out_chars=%d elapsed=%.2fs", mode, len(body), time.monotonic() - t0)
    return f"{body}\n{format_sources_block(sources)}".strip()
