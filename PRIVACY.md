# Privacy

This tool sends the parameters you (or your agent) pass to its methods — `content`, `question`, `bucket`, `memory_id` — to the Engram REST API at `https://api.lumetra.io` (or the self-hosted base URL you configured in Valves). Memories are stored under your Engram tenant, scoped by the API key you provided in the admin or per-user Valves.

The tool does not collect, log, or transmit data to any third party other than the Engram service you've explicitly authorized. The tool does not read other Open WebUI resources (chats, files, knowledge bases) — only the parameters supplied to each tool call.

For Engram's own data-handling and retention policy, see <https://lumetra.io/privacy>.
