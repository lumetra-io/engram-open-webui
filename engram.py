"""
title: Engram Memory
author: Lumetra
author_url: https://lumetra.io
git_url: https://github.com/lumetra-io/engram-open-webui
description: Durable, explainable memory for AI agents. Six tools (store, query, list, delete, clear) backed by the Engram REST API at api.lumetra.io.
required_open_webui_version: 0.4.0
requirements: requests
version: 0.1.0
license: MIT
"""

from __future__ import annotations

from typing import Any, Optional

import requests
from pydantic import BaseModel, Field


class Tools:
    class Valves(BaseModel):
        """Admin-level settings. Set in Workspace -> Tools -> Engram."""

        api_key: str = Field(
            default="",
            description="Engram API key (eng_live_...). Get one at https://lumetra.io.",
            json_schema_extra={"input": {"type": "password"}},
        )
        base_url: str = Field(
            default="https://api.lumetra.io",
            description="Engram REST base URL. Override for self-hosted Engram.",
        )
        default_bucket: str = Field(
            default="default",
            description="Bucket used when a tool call does not specify one.",
        )
        timeout_seconds: int = Field(
            default=60,
            description="HTTP timeout for each Engram API call.",
        )

    class UserValves(BaseModel):
        """Per-user overrides. Configurable from the chat-session settings.

        If a user pastes their own API key here, it takes precedence over the
        admin-level key for that user's tool calls.
        """

        api_key: str = Field(
            default="",
            description="Optional per-user Engram API key. Overrides the admin key when set.",
            json_schema_extra={"input": {"type": "password"}},
        )
        default_bucket: str = Field(
            default="",
            description="Optional per-user default bucket. Overrides the admin default when set.",
        )

    def __init__(self) -> None:
        self.valves = self.Valves()

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _resolve_key(self, __user__: Optional[dict]) -> str:
        user_key = ""
        if __user__ and isinstance(__user__, dict):
            uv = __user__.get("valves")
            user_key = getattr(uv, "api_key", "") if uv is not None else ""
        return (user_key or self.valves.api_key or "").strip()

    def _resolve_bucket(self, bucket: Optional[str], __user__: Optional[dict]) -> str:
        if bucket:
            return bucket
        if __user__ and isinstance(__user__, dict):
            uv = __user__.get("valves")
            user_default = getattr(uv, "default_bucket", "") if uv is not None else ""
            if user_default:
                return user_default
        return self.valves.default_bucket or "default"

    def _headers(self, api_key: str) -> dict:
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "engram-open-webui/0.1.0",
        }

    def _url(self, path: str) -> str:
        base = (self.valves.base_url or "https://api.lumetra.io").rstrip("/")
        return f"{base}{path}"

    def _request(
        self,
        method: str,
        path: str,
        api_key: str,
        json_body: Optional[dict] = None,
        params: Optional[dict] = None,
    ) -> tuple[int, Any]:
        try:
            resp = requests.request(
                method,
                self._url(path),
                headers=self._headers(api_key),
                json=json_body,
                params=params,
                timeout=self.valves.timeout_seconds,
            )
        except requests.RequestException as exc:
            return 0, {"error": f"network error: {exc}"}

        try:
            payload = resp.json()
        except ValueError:
            payload = {"raw": resp.text}
        return resp.status_code, payload

    @staticmethod
    def _missing_key_msg() -> str:
        return (
            "Engram is not configured. Set an API key in Workspace -> Tools -> Engram "
            "(Valves) or in your per-user settings. Get a key at https://lumetra.io."
        )

    # ------------------------------------------------------------------ #
    # Tool methods (exposed to the LLM)
    # ------------------------------------------------------------------ #
    def store_memory(
        self,
        content: str,
        bucket: Optional[str] = None,
        __user__: Optional[dict] = None,
    ) -> str:
        """
        Save an atomic fact or piece of context to Engram memory.

        Store one concept per call for best retrieval quality. Buckets are
        auto-created on first write, so any string works as a bucket name.

        :param content: The fact or text to remember. Required.
        :param bucket: Optional bucket name. Defaults to the configured default bucket.
        :return: JSON string with the new memory's id and status, or an error message.
        """
        api_key = self._resolve_key(__user__)
        if not api_key:
            return self._missing_key_msg()
        if not content or not str(content).strip():
            return "store_memory: 'content' is required."

        bucket_name = self._resolve_bucket(bucket, __user__)
        status, body = self._request(
            "POST",
            f"/v1/buckets/{bucket_name}/memories",
            api_key,
            json_body={"content": str(content)},
        )
        if status in (200, 201):
            mid = body.get("memory_id") or body.get("id") or "unknown"
            return f"Stored in bucket '{bucket_name}'. memory_id={mid}"
        return f"store_memory failed (HTTP {status}): {body}"

    def query_memory(
        self,
        question: str,
        bucket: Optional[str] = None,
        __user__: Optional[dict] = None,
    ) -> str:
        """
        Ask a natural-language question against Engram memory.

        Returns a synthesized answer grounded in the memories stored in the
        given bucket. Call this BEFORE answering user questions whenever
        prior context might be relevant.

        :param question: The natural-language question to ask. Required.
        :param bucket: Optional bucket to search. Defaults to the configured default bucket.
        :return: The synthesized answer string, or an error message.
        """
        api_key = self._resolve_key(__user__)
        if not api_key:
            return self._missing_key_msg()
        if not question or not str(question).strip():
            return "query_memory: 'question' is required."

        bucket_name = self._resolve_bucket(bucket, __user__)
        # Engram REST expects {"query": ...}; we accept "question" from the LLM.
        status, body = self._request(
            "POST",
            "/v1/query",
            api_key,
            json_body={"query": str(question), "bucket": bucket_name},
        )
        if status == 200:
            answer = body.get("answer")
            if answer:
                return str(answer)
            return f"query_memory returned no answer. Raw: {body}"
        return f"query_memory failed (HTTP {status}): {body}"

    def list_memories(
        self,
        bucket: Optional[str] = None,
        limit: int = 20,
        __user__: Optional[dict] = None,
    ) -> str:
        """
        List the most recent memories in a bucket, newest first.

        :param bucket: Optional bucket name. Defaults to the configured default bucket.
        :param limit: Maximum number of memories to return (default 20).
        :return: A formatted list of memories, or an error message.
        """
        api_key = self._resolve_key(__user__)
        if not api_key:
            return self._missing_key_msg()
        bucket_name = self._resolve_bucket(bucket, __user__)
        try:
            limit_int = max(1, min(int(limit), 200))
        except (TypeError, ValueError):
            limit_int = 20

        status, body = self._request(
            "GET",
            f"/v1/buckets/{bucket_name}/memories",
            api_key,
            params={"limit": limit_int},
        )
        if status != 200:
            return f"list_memories failed (HTTP {status}): {body}"

        memories = body.get("memories", []) if isinstance(body, dict) else []
        if not memories:
            return f"Bucket '{bucket_name}' is empty."
        total = body.get("total", len(memories))
        lines = [f"Bucket '{bucket_name}' — {len(memories)} of {total} memories:"]
        for m in memories:
            mid = m.get("id", "?")
            content = (m.get("content") or "").replace("\n", " ").strip()
            created = m.get("created_at", "")
            lines.append(f"- [{mid}] {content}  ({created})")
        return "\n".join(lines)

    def list_buckets(
        self,
        limit: int = 50,
        offset: int = 0,
        __user__: Optional[dict] = None,
    ) -> str:
        """
        List all buckets in the current Engram tenant.

        :param limit: Maximum number of buckets to return (default 50).
        :param offset: Pagination offset (default 0).
        :return: A formatted list of buckets with memory counts, or an error message.
        """
        api_key = self._resolve_key(__user__)
        if not api_key:
            return self._missing_key_msg()
        try:
            limit_int = max(1, min(int(limit), 200))
            offset_int = max(0, int(offset))
        except (TypeError, ValueError):
            limit_int, offset_int = 50, 0

        status, body = self._request(
            "GET",
            "/v1/buckets",
            api_key,
            params={"limit": limit_int, "offset": offset_int},
        )
        if status != 200:
            return f"list_buckets failed (HTTP {status}): {body}"

        buckets = body.get("buckets", []) if isinstance(body, dict) else []
        if not buckets:
            return "No buckets found for this Engram tenant."
        lines = [f"{len(buckets)} bucket(s):"]
        for b in buckets:
            name = b.get("name") or b.get("bucket_name") or "?"
            count = b.get("memory_count", "?")
            lines.append(f"- {name}  ({count} memories)")
        return "\n".join(lines)

    def delete_memory(
        self,
        memory_id: str,
        bucket: str,
        __user__: Optional[dict] = None,
    ) -> str:
        """
        Delete a single memory by its UUID. Destructive — cannot be undone.

        Only call this when the user has explicitly asked to remove a specific
        memory and you have a concrete memory_id from a prior list_memories or
        store_memory call.

        :param memory_id: UUID of the memory to delete. Required.
        :param bucket: Bucket name the memory lives in. Required.
        :return: Confirmation string, or an error message.
        """
        api_key = self._resolve_key(__user__)
        if not api_key:
            return self._missing_key_msg()
        if not memory_id or not str(memory_id).strip():
            return "delete_memory: 'memory_id' is required."
        if not bucket or not str(bucket).strip():
            return "delete_memory: 'bucket' is required."

        status, body = self._request(
            "DELETE",
            f"/v1/buckets/{bucket}/memories/{memory_id}",
            api_key,
        )
        if status == 200:
            return f"Deleted memory {memory_id} from bucket '{bucket}'."
        return f"delete_memory failed (HTTP {status}): {body}"

    def clear_memories(
        self,
        bucket: str,
        __user__: Optional[dict] = None,
    ) -> str:
        """
        Empty an entire bucket. DESTRUCTIVE — wipes every memory in the bucket.

        Only call this when the user has explicitly asked to clear or reset a
        bucket. Always confirm the bucket name with the user before invoking.

        :param bucket: Name of the bucket to empty. Required.
        :return: Confirmation string with cleared_count, or an error message.
        """
        api_key = self._resolve_key(__user__)
        if not api_key:
            return self._missing_key_msg()
        if not bucket or not str(bucket).strip():
            return "clear_memories: 'bucket' is required."

        status, body = self._request(
            "DELETE",
            f"/v1/buckets/{bucket}/memories",
            api_key,
        )
        if status == 200:
            cleared = body.get("cleared_count", "?") if isinstance(body, dict) else "?"
            return f"Cleared bucket '{bucket}'. cleared_count={cleared}"
        return f"clear_memories failed (HTTP {status}): {body}"
