"""Provider-discovery endpoints — fetch the list of models exposed by an
OpenAI-compatible endpoint so the UI can populate a dropdown."""
from __future__ import annotations

from fastapi import APIRouter, Query
from openai import AsyncOpenAI

from ..models import ModelsResponse

router = APIRouter(prefix="/api/provider", tags=["provider"])


@router.get("/models", response_model=ModelsResponse)
async def list_models(
    base_url: str = Query(..., description="OpenAI-compatible base URL"),
    api_key: str = Query("", description="API key — any non-empty value works for local endpoints"),
) -> ModelsResponse:
    client = AsyncOpenAI(base_url=base_url, api_key=api_key or "not-needed")
    try:
        page = await client.models.list()
    except Exception as exc:
        return ModelsResponse(models=[], error=str(exc))
    ids = sorted({m.id for m in getattr(page, "data", []) if getattr(m, "id", None)})
    return ModelsResponse(models=ids)
