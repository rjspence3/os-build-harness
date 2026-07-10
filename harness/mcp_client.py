"""OutSystems MCP client for the banking app runner.

Strategy: spawn `npx -y mcp-remote <tenant>/mcp` as a stdio subprocess. The
mcp-remote npm package handles OAuth (Dynamic Client Registration + browser
callback flow) on first run and caches the token. We speak JSON-RPC over its
stdin/stdout using the official Python `mcp` SDK's stdio_client.

This avoids reimplementing OAuth + token caching in Python while still letting
the runner work unattended after the first interactive auth.

API exposed:
    async with MentorMCP(tenant="...") as mcp:
        run_id = await mcp.mentor_start(app_key, prompt)
        result = await mcp.mentor_poll(run_id, max_wait_seconds=300)
        publish_id = await mcp.publish_start(app_key)
        await mcp.publish_wait(publish_id)
        entities = await mcp.context_entities(app_key)

Errors surface as MentorError with the verbatim stderr / status payload.

Status: stdio bridge wired; mentor_start/poll smoke-tested. publish_* + context_*
covered.
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


DEFAULT_TENANT = os.getenv("OUTSYSTEMS_MCP_TENANT", "your-tenant.outsystems.dev")
DEFAULT_POLL_SECONDS = 2.0
DEFAULT_TIMEOUT_SECONDS = 300


class MentorError(Exception):
    """Raised when an MCP tool call fails or a polled run terminates in 'failed'."""


@dataclass
class MentorRunResult:
    """Final state of a mentor_get_run call."""
    run_id: str
    status: str                          # 'succeeded' | 'failed' | 'cancelled' | 'running' (if timeout)
    stdout: str                          # last applyModelApiCode tool_end stdoutOutput
    compile_errors: list[str]
    summary: str
    session_id: Optional[str]
    session_token: Optional[str]
    raw_events: list[dict[str, Any]]
    error: Optional[str] = None          # terminal error code/message (e.g. per_tenant_cap_reached)


class MentorMCP:
    """Async context manager wrapping the mcp-remote stdio bridge to OutSystems MCP."""

    def __init__(self, tenant: str = DEFAULT_TENANT):
        self.tenant = tenant
        self.server_url = f"https://{tenant}/mcp"
        self._session: Optional[ClientSession] = None
        self._cm = None  # context manager guard

    async def __aenter__(self) -> "MentorMCP":
        # Spawn `npx -y mcp-remote https://<tenant>/mcp` as a stdio MCP server
        params = StdioServerParameters(
            command="npx",
            args=["-y", "mcp-remote", self.server_url],
            env={**os.environ},
        )
        self._cm = stdio_client(params)
        read_stream, write_stream = await self._cm.__aenter__()
        self._session = ClientSession(read_stream, write_stream)
        await self._session.__aenter__()
        await self._session.initialize()
        return self

    async def __aexit__(self, *exc_info) -> None:
        if self._session:
            await self._session.__aexit__(*exc_info)
            self._session = None
        if self._cm:
            await self._cm.__aexit__(*exc_info)
            self._cm = None

    async def _call(self, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call an MCP tool by name; return parsed JSON payload (first text content)."""
        assert self._session, "MentorMCP must be used as async context manager"
        result = await self._session.call_tool(tool, arguments)
        if result.isError:
            content_text = _flatten_content(result.content)
            raise MentorError(f"MCP tool {tool} returned error: {content_text}")
        # Tool returns one text-block with JSON payload
        text = _flatten_content(result.content)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Some tools return plain text — wrap in dict for consistency
            return {"_raw": text}

    # ─── Mentor: applyModelApiCode flow ───────────────────────────────────────

    async def mentor_start(self, app_key: Optional[str] = None, prompt: str = "", *,
                           session_id: Optional[str] = None, session_token: Optional[str] = None,
                           fresh_context: bool = False) -> str:
        """Start a Mentor run. Returns run_id.

        First turn of a session: pass `app_key`. RESUME turn (reuse the SAME session + its
        per-tenant slot — the session-economy path): pass `session_id` + `session_token` (from the
        prior turn's terminal result) and `fresh_context=True` to start a clean conversation over the
        session's current OML WITHOUT opening a new slot. This is how a build spends ONE slot for many
        steps instead of one-per-step (the greedy default that saturates the 100-cap)."""
        if session_id and session_token:
            args = {"mentor_session_id": session_id, "mentor_session_token": session_token, "prompt": prompt}
            if fresh_context:
                args["fresh_context"] = True
        else:
            args = {"app_key": app_key, "prompt": prompt}
        payload = await self._call("mentor_start", args)
        run_id = payload.get("runId") or payload.get("run_id")
        if not run_id:
            raise MentorError(f"mentor_start returned no runId: {payload}")
        return run_id

    async def mentor_get_run(self, run_id: str, cursor: Optional[str] = None) -> dict[str, Any]:
        args: dict[str, Any] = {"runId": run_id}
        if cursor:
            args["cursor"] = cursor
        return await self._call("mentor_get_run", args)

    async def mentor_poll(
        self,
        run_id: str,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        poll_seconds: float = DEFAULT_POLL_SECONDS,
    ) -> MentorRunResult:
        """Poll until terminal. Aggregates events across polls via nextCursor."""
        deadline = time.monotonic() + timeout_seconds
        cursor: Optional[str] = None
        all_events: list[dict[str, Any]] = []
        last_payload: dict[str, Any] = {}

        while True:
            payload = await self.mentor_get_run(run_id, cursor=cursor)
            last_payload = payload
            events = payload.get("events", []) or []
            all_events.extend(events)
            cursor = payload.get("nextCursor") or cursor
            status = payload.get("status", "running")

            if status in ("succeeded", "failed", "cancelled"):
                return _build_run_result(run_id, status, last_payload, all_events)

            if time.monotonic() > deadline:
                # Treat as in-flight timeout — caller decides
                return _build_run_result(run_id, "running", last_payload, all_events)

            await asyncio.sleep(poll_seconds)

    async def mentor_cancel(self, run_id: str) -> None:
        await self._call("mentor_cancel", {"runId": run_id})

    # ─── Publish ──────────────────────────────────────────────────────────────

    DEV_ENV_KEY = ""  # your ODC Dev environment key (from env_list); blank by default so no tenant
    #                   value ships — set it in your fork or pass env_key explicitly. TODO: read from env_list.

    async def publish_start(
        self,
        mentor_session_id: str,
        mentor_session_token: str,
        env_key: str = DEV_ENV_KEY,
    ) -> str:
        """Publish the OML accumulated in a Mentor session. Fire-and-return: returns the
        `operation_id` to poll `publish_status` with.

        Per the live OutSystems MCP contract (verified via the HarnessCanary canary 2026-07-08):
        the HTTP response is `{operation_id, state:'pending', application_key, message}` — the
        `app_key` is taken from the signed token, not from arguments. Each MentorRunResult carries
        its own session_id + token at the terminal-success poll.
        """
        payload = await self._call("publish_start", {
            "mentor_session_id": mentor_session_id,
            "mentor_session_token": mentor_session_token,
            "env_key": env_key,
        })
        pid = (payload.get("operation_id") or payload.get("publication_id")
               or payload.get("key") or payload.get("operationKey"))
        if not pid:
            raise MentorError(f"publish_start returned no operation_id: {payload}")
        return pid

    async def publish_status(self, publication_id: str) -> dict[str, Any]:
        return await self._call("publish_status", {"publication_id": publication_id})

    async def publish_logs(self, pub_key: str) -> dict[str, Any]:
        """The build-engine publication MESSAGES for a publication (the real per-element compile
        errors behind a generic OS-BEW/OS-DPL code). Best-effort — returns {} if unavailable."""
        try:
            return await self._call("publish_logs", {"pub_key": pub_key})
        except Exception:
            return {}

    # Terminal publish states (live contract): `state` ∈ pending|succeeded|failed. A legacy
    # `status` ∈ Finished|Failed|Cancelled is also accepted for stdio/older transports.
    _PUBLISH_TERMINAL = {"succeeded", "failed", "cancelled"}
    _PUBLISH_TERMINAL_LEGACY = {"Finished", "Failed", "Cancelled"}

    async def publish_wait(self, publication_id: str, timeout_seconds: int = 600) -> dict[str, Any]:
        """Poll publish_status until terminal, returning the final payload. Terminal is
        `state` ∈ {succeeded, failed, cancelled} (the live HTTP contract) or a legacy
        `status` ∈ {Finished, Failed, Cancelled}. `state:pending` keeps polling."""
        deadline = time.monotonic() + timeout_seconds
        while True:
            payload = await self.publish_status(publication_id)
            state = (payload.get("state") or "").lower()
            status = payload.get("status") or ""
            if state in self._PUBLISH_TERMINAL or status in self._PUBLISH_TERMINAL_LEGACY:
                return payload
            if time.monotonic() > deadline:
                raise MentorError(f"publish_wait timed out for {publication_id} "
                                  f"(last state={state or status})")
            await asyncio.sleep(5.0)

    # ─── Context (verification reads) ──────────────────────────────────────────

    async def context_entities(self, app_key: str, limit: int = 100, owned_only: bool = True) -> dict[str, Any]:
        return await self._call(
            "context_entities", {"app": app_key, "limit": limit, "owned_only": owned_only}
        )

    async def context_actions(self, app_key: str, limit: int = 100) -> dict[str, Any]:
        return await self._call("context_actions", {"app": app_key, "limit": limit})

    async def context_screens(self, app_key: str, limit: int = 100) -> dict[str, Any]:
        return await self._call("context_screens", {"app": app_key, "limit": limit, "owned_only": True})

    async def context_roles(self, app_key: str, limit: int = 50) -> dict[str, Any]:
        return await self._call("context_roles", {"app": app_key, "limit": limit})

    async def app_info(self, app_key: str) -> dict[str, Any]:
        return await self._call("app_info", {"key": app_key})

    async def app_list(self, search: Optional[str] = None) -> dict[str, Any]:
        args = {"search": search} if search else {}
        return await self._call("app_list", args)

    async def env_list(self) -> dict[str, Any]:
        """List the tenant's ODC environments (for resolving the Dev env_key publish target)."""
        return await self._call("env_list", {})

    async def env_app(self, app_key: str, env_key: str) -> dict[str, Any]:
        """The deployed app's runtime details (incl. `url`) in an environment — used to reach a built
        app (e.g. load its Home to fire the OnReady seed, or hand the user the link)."""
        return await self._call("env_app", {"key": app_key, "env_key": env_key})

    async def app_create(self, name: str, kind: str = "CrossDevice") -> dict[str, Any]:
        """Create a new ODC app. kind ∈ {CrossDevice(→WebApplication), BusinessProcess, AIAgent,
        MCPConnection}. Returns the raw payload; the caller resolves the app key (via this payload
        or app_list) since the key field name varies across ODC responses."""
        return await self._call("app_create", {"name": name, "kind": kind})


# ─── Helpers ───────────────────────────────────────────────────────────────────

def _flatten_content(content_list) -> str:
    """MCP CallToolResult.content is a list of content blocks. Extract text."""
    parts = []
    for c in (content_list or []):
        text = getattr(c, "text", None)
        if text:
            parts.append(text)
    return "".join(parts)


def _build_run_result(
    run_id: str,
    status: str,
    last_payload: dict[str, Any],
    events: list[dict[str, Any]],
) -> MentorRunResult:
    """Reduce the streamed event list to a terminal-state RunResult."""
    # Find the LAST tool_end with name=applyModelApiCode and extract stdout / errors
    stdout = ""
    compile_errors: list[str] = []
    for ev in events:
        if ev.get("type") == "tool_end" and ev.get("name") == "applyModelApiCode":
            try:
                inner = json.loads(ev["result"]) if isinstance(ev.get("result"), str) else (ev.get("result") or {})
            except (json.JSONDecodeError, TypeError):
                inner = {}
            if inner.get("stdoutOutput"):
                stdout = inner["stdoutOutput"]
            if inner.get("compilationErrors"):
                compile_errors = list(inner["compilationErrors"])

    result_block = last_payload.get("result") or {}
    summary = (result_block.get("summary") or last_payload.get("message") or "").strip()
    session_id = result_block.get("mentor_session_id")
    session_token = result_block.get("mentor_session_token")

    # Surface the terminal `error` (e.g. per_tenant_cap_reached) — previously swallowed, so a
    # capacity/auth failure looked like a bare "failed" and got pointlessly retried.
    err = last_payload.get("error")
    if isinstance(err, dict):
        error = ": ".join(x for x in (err.get("code"), err.get("message")) if x) or None
    else:
        error = err or None

    return MentorRunResult(
        run_id=run_id,
        status=status,
        stdout=stdout,
        compile_errors=compile_errors,
        summary=summary,
        session_id=session_id,
        session_token=session_token,
        raw_events=events,
        error=error,
    )
