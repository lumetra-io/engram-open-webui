# engram-open-webui

[Open WebUI](https://github.com/open-webui/open-webui) integration for [Engram](https://lumetra.io) — durable, explainable memory for the popular self-hosted local-AI UI.

Adds the six Engram tools — `store_memory`, `query_memory`, `list_memories`, `list_buckets`, `delete_memory`, `clear_memories` — to any model you run through Open WebUI. Works by running Open WebUI's own [`mcpo`](https://github.com/open-webui/mcpo) bridge in front of the Engram MCP endpoint, then plugging that into Open WebUI's External Tools panel.

## Why a bridge?

Open WebUI's "External Tools" panel speaks **Streamable HTTP MCP** (or OpenAPI). The hosted Engram MCP server is currently **SSE-only**. The Open WebUI team's official answer for this is `mcpo` — a tiny proxy that exposes any MCP server (any transport) as an OpenAPI-compatible HTTP server. It's the cleanest path today and disappears the moment Engram ships native Streamable HTTP.

## Setup

### 1. Get an Engram API key

Sign up at <https://lumetra.io> — free tier, no card. You'll see an `eng_live_…` token in your dashboard.

```bash
export ENGRAM_API_KEY="eng_live_..."
```

### 2. Configure a BYOK provider key

Engram is bring-your-own-key end-to-end for the LLM that handles extraction and synthesis. Configure one provider at <https://lumetra.io/models>. DeepSeek is what we recommend — cheap and fast. Without a provider key, every `store_memory` / `query_memory` returns HTTP 412.

### 3. Run the `mcpo` bridge pointing at Engram

```bash
pip install mcpo

# Drop this somewhere persistent (the bridge needs to be running for tools to work)
cat > ~/.config/mcpo/engram.json <<JSON
{
  "mcpServers": {
    "engram": {
      "type": "sse",
      "url": "https://mcp.lumetra.io/mcp/sse",
      "headers": {
        "Authorization": "Bearer eng_live_..."
      }
    }
  }
}
JSON

mcpo --port 8001 --config ~/.config/mcpo/engram.json
```

You should see:

```
INFO - Successfully connected to 'engram'.
INFO - Uvicorn running on http://0.0.0.0:8001
```

Verify the OpenAPI surface:

```bash
curl http://127.0.0.1:8001/engram/openapi.json | head
# Should show paths /store_memory, /query_memory, /list_buckets, /list_memories, /delete_memory, /clear_memories
```

### 4. Wire Open WebUI to the bridge

In Open WebUI, go to **Admin Settings → External Tools → + Add Server**. Use the **OpenAPI** tab — [`mcpo`](https://github.com/open-webui/mcpo) exposes an OpenAPI surface only, not Streamable HTTP MCP, so the **MCP (Streamable HTTP)** tab will not work against this bridge. Set the URL to:

```
http://localhost:8001/engram
```

Save. The six Engram tools now appear under External Tools and can be enabled per-model.

## Tools exposed

| Tool | What it does |
|---|---|
| `store_memory(content, bucket?)` | Save a fact to a bucket (defaults to `"default"`). |
| `query_memory(question, bucket?)` | Hybrid retrieval + synthesized answer with citations. |
| `list_memories(bucket, limit?)` | Newest-first list of memories in a bucket. |
| `list_buckets(limit?, offset?)` | Paginated list of all buckets in your tenant. |
| `delete_memory(memory_id, bucket)` | Remove a single memory. |
| `clear_memories(bucket)` | Empty a bucket. Destructive. |

## Production tips

- **Keep `mcpo` running** as a systemd service / docker-compose service / supervisor job. If `mcpo` is down, Open WebUI gets a tool-call error.
- **Set `WEBUI_SECRET_KEY`** in your Open WebUI env so OAuth-connected tools don't break on container restart.
- **Don't expose port 8001 publicly** — `mcpo` is meant to sit behind Open WebUI on the same host (or behind your reverse proxy with auth). It carries your Engram API key in cleartext per request.

## Verified

Smoke-tested end-to-end:

- `mcpo --config …` connected to `mcp.lumetra.io/mcp/sse` and exposed `LumetraMemory` as an OpenAPI server with the six expected endpoints.
- `POST http://127.0.0.1:8001/engram/store_memory` returned a real `memory_id` and `status=stored`.
- `POST http://127.0.0.1:8001/engram/list_memories` returned the just-stored memory with the correct content and timestamp.

## License

MIT — Lumetra
