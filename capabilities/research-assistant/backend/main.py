from __future__ import annotations

import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import provider, research

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    datefmt="%H:%M:%S",
)
# Quiet down chatty third-party loggers; keep ours at INFO.
for noisy in ("httpx", "httpcore", "openai", "primp", "ddgs"):
    logging.getLogger(noisy).setLevel(logging.WARNING)
logging.getLogger("research_assistant").setLevel(
    os.getenv("LOG_LEVEL", "INFO").upper()
)

app = FastAPI(title="Research Assistant", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(provider.router)
app.include_router(research.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
