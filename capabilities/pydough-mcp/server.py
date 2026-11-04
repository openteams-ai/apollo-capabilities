"""PyDough analytics MCP server.

Run via:  pixi run launch
Or:       python server.py

Environment variables:
  PYDOUGH_MCP_HOST   bind address (default 127.0.0.1)
  PYDOUGH_MCP_PORT   port (default 8765)

Credentials read by the PyDough session tools at query time:
  OPENAI_API_KEY     bearer token for the LLM provider — passed to aisuite
  OPENAI_BASE_URL    LLM base URL (OpenAI-compatible endpoint) — passed to aisuite

FastMCP 1.x reads host/port from server.settings, not from run() kwargs.
"""
from __future__ import annotations

import os
import sys

host = os.getenv("PYDOUGH_MCP_HOST", "127.0.0.1")
port = int(os.getenv("PYDOUGH_MCP_PORT", "8765"))

try:
    from pydough_analytics.mcp.server import server
except ImportError as exc:
    print(f"[pydough-mcp] import error: {exc}", file=sys.stderr)
    sys.exit(1)

server.settings.host = host
server.settings.port = port

# SSE transport: FastMCP mounts GET /sse and POST /messages/
# pydantic-ai MCPServerSSE connects to http://<host>:<port>/sse
print(f"[pydough-mcp] starting SSE server — connect at http://{host}:{port}/sse", flush=True)

server.run(transport="sse")
