## PyDough MCP

A background MCP server that exposes PyDough analytics tools over SSE HTTP. Collab hub agents connect to it as an MCP client and use it to translate natural-language data questions into PyDough/SQL queries, which are then executed against a configured database.

Requires: `pixi` ([install](https://pixi.sh/latest/#installation))

```bash
OPENAI_API_KEY=<key> OPENAI_BASE_URL=<llm-base-url> pixi run launch
```

The server binds to `http://127.0.0.1:8765/sse` by default.

### Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `PYDOUGH_MCP_HOST` | `127.0.0.1` | Bind address |
| `PYDOUGH_MCP_PORT` | `8765` | Port |
| `OPENAI_API_KEY` | — | Bearer token for the LLM provider (passed to aisuite at query time) |
| `OPENAI_BASE_URL` | — | OpenAI-compatible LLM base URL (Hub endpoint or OpenRouter) |

### How it works

1. A Collab hub agent receives a data question from the user.
2. The agent calls `open_session_impl` with the database URL, metadata path, db name, and graph name.
3. The agent calls `ask_impl` — the MCP server uses the configured LLM to generate a PyDough expression, compiles it to SQL, and executes it.
4. The agent calls `close_session_impl` and reports the rows, SQL, and any errors.

### Companion

The [`ravnar-apollo`](https://github.com/openteams-ai/apollo-desktop) hub agent attaches to this server via `MCPServerSSE` when `PYDOUGH_MCP_URL` is set in its environment.
