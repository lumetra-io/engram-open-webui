# engram-open-webui

[Engram](https://lumetra.io) memory tools for [Open WebUI](https://openwebui.com) — durable, explainable memory for AI agents.

This is a native Open WebUI **Tools** plugin: a single Python file that registers six callable tools backed by the hosted Engram REST API at `api.lumetra.io`. No `mcpo` bridge, no OpenAPI server, no extra container — just upload `engram.py` in the admin UI and the tools appear in the workspace tool catalog.

## Install

### Option A — paste into the admin UI (fastest)

1. Open Open WebUI as an admin.
2. Go to **Workspace -> Tools -> +** (the *Create new tool* button).
3. Paste the contents of [`engram.py`](./engram.py) into the editor and click **Save**.
4. Open the tool's settings (the gear icon) and fill in **Valves**:
   - **API key**: your `eng_live_...` token from <https://lumetra.io>
   - **Base URL**: leave as `https://api.lumetra.io` unless you self-host Engram
   - **Default bucket**: `default` is fine; change per project as needed
5. In any chat that should have memory, enable the **Engram Memory** tool from the model's `+` menu.

### Option B — community hub (after we publish)

Search for **Engram Memory** on <https://openwebui.com/tools> and click **Get** to import directly into your Open WebUI instance. You'll still configure the Valves the first time you use it.

## Configure a BYOK provider key

Engram is bring-your-own-key for the LLM that powers extraction and synthesis. Configure one provider at <https://lumetra.io/models> — we recommend **DeepSeek** (cheap and fast). Without a provider key, `store_memory` and `query_memory` return HTTP 412 from the Engram API.

## Tools

| Tool | What it does |
|---|---|
| `store_memory(content, bucket?)` | Save an atomic fact to a bucket. Buckets auto-create on first write. |
| `query_memory(question, bucket?)` | Ask a natural-language question against memory. Returns a synthesized answer. |
| `list_memories(bucket?, limit?)` | Newest-first list of memories in a bucket. |
| `list_buckets(limit?, offset?)` | Paginated list of buckets in your tenant. |
| `delete_memory(memory_id, bucket)` | Remove a single memory by UUID. |
| `clear_memories(bucket)` | Empty a bucket. **Destructive.** |

## Per-user API keys

Set a tenant-wide key as an admin in **Valves**. If individual users want to use their own Engram tenant, they can paste their key into **UserValves** from the in-chat settings; the per-user key takes precedence when present.

## Self-hosted Engram

If you run Engram on your own infrastructure instead of `api.lumetra.io`, set **Base URL** in the admin Valves to your endpoint (for example, `https://engram.internal.example.com`). The tools will hit the same `/v1/...` paths there.

## Manual verification

Outside Open WebUI, confirm Engram itself is reachable with your key:

```bash
curl -s https://api.lumetra.io/v1/buckets \
  -H "Authorization: Bearer eng_live_..." | head -c 300
```

A JSON bucket list confirms the key is valid. If Open WebUI shows the tool but calls fail, double-check the API key in Valves and that your Open WebUI process can reach `api.lumetra.io`.

## Source & contact

- Source: <https://github.com/lumetra-io/engram-open-webui>
- Issues: <https://github.com/lumetra-io/engram-open-webui/issues>
- Lumetra: <https://lumetra.io> · <support@lumetra.io>

## License

MIT — Lumetra
