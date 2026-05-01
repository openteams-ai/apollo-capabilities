from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

OutputMode = Literal["summary", "report", "pros_cons", "timeline", "open_questions"]


class ProviderConfig(BaseModel):
    base_url: str = Field(..., description="OpenAI-compatible base URL, e.g. https://api.openai.com/v1")
    api_key: str = Field("", description="Bearer token; any non-empty string for local endpoints")
    model: str = Field(..., description="Model id, e.g. gpt-4o, llama3.2")


class ResearchRequest(BaseModel):
    topic: str
    output_mode: OutputMode = "summary"
    provider: ProviderConfig


class FollowUpRequest(BaseModel):
    question: str
    provider: ProviderConfig
    output_mode: OutputMode | None = None


class Source(BaseModel):
    title: str
    url: str
    snippet: str = ""


class ResearchResponse(BaseModel):
    session_id: str
    output_mode: OutputMode
    content: str
    sources: list[Source]


class StartResponse(BaseModel):
    session_id: str


class ModelsResponse(BaseModel):
    models: list[str]
    error: str | None = None


SessionState = dict[str, Any]
