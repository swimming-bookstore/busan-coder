from __future__ import annotations

import json
import uuid
from typing import Any, Callable

from fighter.auth import AuthStore
from fighter.httpjson import CTX

from fighter.agent import Agent


class Reply:
    def __init__(self) -> None:
        self.text = ""
        self.thinking = ""
        self.calls: list[dict[str, Any]] = []
        self.truncated = False
        self.input_tokens = 0
        self.output_tokens = 0
        self.cached_tokens = 0
        self.reasoning_tokens = 0


def is_think_delta(typ: str) -> bool:
    t = typ.lower()
    return (
        ("reason" in t or "think" in t)
        and (t.endswith(".delta") or t.endswith(".text") or "summary" in t)
        and "function_call" not in t
    )


def apply_sse(
    typ: str,
    v: dict[str, Any],
    r: Reply,
    calls: list[dict[str, str]],
    on_delta: Callable[[str], None],
    on_think: Callable[[str], None],
) -> None:
    if is_think_delta(typ):
        d = v.get("delta") or v.get("text") or ""
        if isinstance(d, str) and d:
            r.thinking += d
            on_think(d)
        return
    if typ.endswith("output_text.delta") or typ.endswith("text.delta"):
        d = v.get("delta") or ""
        if isinstance(d, str) and d:
            r.text += d
            on_delta(d)
        return
    if typ.endswith("output_item.added") or typ.endswith("output_item.done"):
        item = v.get("item") or {}
        if item.get("type") == "function_call":
            item_id = item.get("id") or ""
            existing = next((c for c in calls if item_id and c["item_id"] == item_id), None)
            if existing:
                if item.get("arguments") and not existing["arguments"]:
                    existing["arguments"] = item.get("arguments") or ""
                return
            calls.append(
                {
                    "item_id": item_id,
                    "call_id": item.get("call_id") or "",
                    "name": item.get("name") or "",
                    "arguments": item.get("arguments") or "",
                }
            )
        return
    if typ.endswith("function_call_arguments.delta"):
        d = v.get("delta") or ""
        item_id = v.get("item_id") or ""
        for c in reversed(calls):
            if not item_id or c["item_id"] == item_id:
                c["arguments"] += d
                break
        return
    if typ.endswith("completed") or typ.endswith("incomplete"):
        if typ.endswith("incomplete"):
            r.truncated = True
        resp = v.get("response") or {}
        usage = resp.get("usage") or {}
        r.input_tokens = int(usage.get("input_tokens") or 0)
        r.output_tokens = int(usage.get("output_tokens") or 0)
        r.cached_tokens = int((usage.get("input_tokens_details") or {}).get("cached_tokens") or 0)
        r.reasoning_tokens = int((usage.get("output_tokens_details") or {}).get("reasoning_tokens") or 0)
        if not r.text:
            r.text = resp.get("output_text") or r.text


def to_input(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for e in entries:
        kind = e.get("kind")
        if kind == "user":
            out.append({"role": "user", "content": e.get("text") or ""})
        elif kind == "assistant":
            if e.get("text"):
                out.append({"role": "assistant", "content": e["text"]})
            for c in e.get("calls") or []:
                out.append(
                    {
                        "type": "function_call",
                        "call_id": c["id"],
                        "name": c["name"],
                        "arguments": json.dumps(c.get("args") or {}),
                    }
                )
        elif kind == "tool":
            out.append(
                {
                    "type": "function_call_output",
                    "call_id": e["id"],
                    "output": e.get("content") or "",
                }
            )
    return out


def grok_complete(
    agent: Agent,
    session: list[dict[str, Any]],
    auth: AuthStore,
    on_delta: Callable[[str], None],
    on_think: Callable[[str], None],
    alive: Callable[[], bool] | None = None,
    aborted: Callable[[], bool] | None = None,
) -> Reply:
    import http.client
    from urllib.parse import urlparse

    token = auth.bearer()
    body = json.dumps(
        {
            "model": agent.config.model,
            "instructions": agent.system_prompt(),
            "input": to_input(session),
            "tools": agent.tool_schemas(),
            "stream": True,
            "reasoning": {"effort": agent.effort()},
        }
    ).encode()
    u = urlparse(agent.config.base_url)
    conn = http.client.HTTPSConnection(u.netloc, timeout=90, context=CTX)
    path = (u.path.rstrip("/") + "/responses") if u.path else "/responses"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "text/event-stream",
        "Accept-Encoding": "identity",
        "Content-Type": "application/json",
    }
    conn.request("POST", path, body=body, headers=headers)
    resp = conn.getresponse()
    if resp.status == 401:
        t = auth.load()
        if t and t.get("refresh"):
            t = auth.refresh(t["refresh"])
            auth.save(t)
            token = t["access"]
            headers["Authorization"] = f"Bearer {token}"
            conn.close()
            conn = http.client.HTTPSConnection(u.netloc, timeout=90, context=CTX)
            conn.request("POST", path, body=body, headers=headers)
            resp = conn.getresponse()
    if resp.status >= 300:
        err = resp.read().decode("utf-8", "replace")[:800]
        conn.close()
        raise RuntimeError(f"grok {resp.status}: {err}")
    r = Reply()
    calls: list[dict[str, str]] = []
    buf = ""
    while True:
        if (aborted and aborted()) or (alive is not None and not alive()):
            conn.close()
            raise RuntimeError("aborted")
        chunk = resp.read(4096)
        if not chunk:
            break
        buf += chunk.decode("utf-8", "replace")
        buf = buf.replace("\r\n", "\n").replace("\r", "\n")
        while "\n\n" in buf:
            block, buf = buf.split("\n\n", 1)
            event = ""
            data = ""
            for line in block.split("\n"):
                if not line or line.startswith(":"):
                    continue
                if line.startswith("event:"):
                    event = line[6:].strip()
                elif line.startswith("data:"):
                    data = (data + "\n" if data else "") + line[5:].lstrip()
                elif line.startswith("{"):
                    data = line
            if not data or data == "[DONE]":
                continue
            try:
                v = json.loads(data)
            except json.JSONDecodeError:
                continue
            typ = event or str(v.get("type") or "")
            apply_sse(typ, v, r, calls, on_delta, on_think)
    conn.close()
    r.calls = []
    for c in calls:
        try:
            args = json.loads(c["arguments"] or "{}")
        except json.JSONDecodeError:
            args = {}
        if not isinstance(args, dict):
            args = {}
        r.calls.append(
            {
                "id": c["call_id"] or str(uuid.uuid4()),
                "name": c["name"],
                "args": args,
            }
        )
    return r
