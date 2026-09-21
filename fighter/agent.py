from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fighter.tools import Tool, builtin_tools, clip, file_preview, tool_path, ungutter, write_body

PKG = Path(__file__).resolve().parent
ROOT = PKG.parent


@dataclass
class AgentConfig:
    name: str = "Busan Coder"
    callsign: str = "BUSAN"
    workspace: Path = field(default_factory=lambda: ROOT)
    extra_instructions: str = ""
    model: str = field(default_factory=lambda: os.environ.get("FUN_CODING_AGENT_MODEL", "grok-4.6"))
    effort: str = field(default_factory=lambda: os.environ.get("FUN_CODING_AGENT_EFFORT", "medium"))
    base_url: str = field(default_factory=lambda: os.environ.get("FUN_CODING_AGENT_BASE_URL", "https://api.x.ai/v1").rstrip("/"))
    max_rounds: int = 32
    html: Path = field(default_factory=lambda: PKG / "pad.html")
    host: str = "127.0.0.1"
    port: int = 8765
    open_browser: bool = True
    record_prompt: str = "fix the tests in demo/"


class Agent:
    """A fighter coding agent: identity + workspace + tools + Grok loop."""

    def __init__(
        self,
        name: str = "Busan Coder",
        *,
        callsign: str = "BUSAN",
        workspace: str | Path | None = None,
        extra_instructions: str = "",
        tools: list[Tool] | None = None,
        extra_tools: list[Tool] | None = None,
        model: str | None = None,
        effort: str | None = None,
        config: AgentConfig | None = None,
    ) -> None:
        cfg = config or AgentConfig()
        cfg.name = name or cfg.name
        cfg.callsign = callsign or cfg.callsign
        if workspace is not None:
            cfg.workspace = Path(workspace).resolve()
        else:
            cfg.workspace = Path(cfg.workspace).resolve()
        if extra_instructions:
            cfg.extra_instructions = extra_instructions
        if model:
            cfg.model = model
        if effort:
            cfg.effort = effort
        self.config = cfg
        self.tools: dict[str, Tool] = {}
        for t in tools if tools is not None else builtin_tools(cfg.workspace):
            self.add_tool(t)
        for t in extra_tools or []:
            self.add_tool(t)

    def add_tool(self, t: Tool) -> None:
        self.tools[t.name] = t

    def tool_schemas(self) -> list[dict[str, Any]]:
        return [t.schema() for t in self.tools.values()]

    def system_prompt(self) -> str:
        names = ", ".join(self.tools)
        extra = ("\n" + self.config.extra_instructions.strip()) if self.config.extra_instructions.strip() else ""
        return (
            f"You are {self.config.name} coding agent. Tools: {names}.\n"
            "Read a file before editing it. Prefer edit for small changes.\n"
            "Paths are relative to this workspace unless absolute. read, write, and edit may use paths outside the workspace.\n"
            "bash times out after 30s; pass timeout (seconds, max 600) for longer commands. Verify with tools before claiming done. Keep replies short.\n"
            f"workspace: {self.config.workspace}"
            f"{extra}"
        )

    def effort(self) -> str:
        e = (self.config.effort or "medium").lower()
        if e in ("low", "minimal"):
            return "low"
        if e in ("high", "xhigh", "x-high"):
            return "high"
        return "medium"

    def run_tool(self, name: str, args: dict[str, Any]) -> tuple[str, bool, str | None]:
        tool = self.tools.get(name) or self.tools.get(name.strip().split(".")[-1].lower())
        if tool is None:
            return f"unknown tool {name}", True, None
        try:
            out = tool.handler(args)
            kind = tool.kind or tool.name
            preview = (
                file_preview(self.config.workspace, kind, args, out)
                if kind in ("read", "write", "edit")
                else (out[:8000] if kind == "bash" else None)
            )
            return out, False, preview
        except subprocess.TimeoutExpired:
            return "timeout", True, None
        except Exception as e:
            kind = (tool.kind if tool else "") or name
            preview = None
            if kind in ("read", "write", "edit", "bash"):
                try:
                    preview = file_preview(self.config.workspace, kind, args, str(e)) if kind != "bash" else str(e)[:8000]
                except Exception:
                    preview = None
            return str(e), True, preview

    def tool_payload(self, name: str, args: dict[str, Any], detail: str, is_error: bool, preview: str | None) -> dict[str, Any]:
        kind = name.strip().split(".")[-1].lower()
        tool = self.tools.get(kind)
        if tool:
            kind = tool.kind or tool.name
        path = tool_path(args)
        args_s = json.dumps(args or {}, ensure_ascii=False)
        if len(args_s) > 180:
            args_s = args_s[:177] + "..."
        if preview is None and kind == "read" and detail:
            preview = ungutter(detail)[:8000]
        payload: dict[str, Any] = {
            "name": kind or name,
            "args": args_s,
            "detail": clip(detail, 4000),
            "is_error": is_error,
            "path": path or None,
            "preview": preview,
        }
        if kind == "edit":
            payload["edit_new"] = str(args.get("new") or "")[:8000]
            payload["edit_old"] = str(args.get("old") or "")[:8000]
        if kind == "write":
            payload["preview"] = write_body(args)[:8000] or (preview or "")[:8000]
            payload["content"] = payload["preview"]
        if kind == "bash":
            payload["cmd"] = str(args.get("cmd") or "")[:400]
            if payload.get("preview") is None:
                payload["preview"] = clip(detail, 8000)
        return payload

    def edit_orig(self, args: dict[str, Any]) -> str:
        path = tool_path(args)
        if not path:
            return ""
        try:
            p = self.config.workspace / path if not Path(path).is_absolute() else Path(path)
            p = p.expanduser().resolve()
            if p.is_file():
                return p.read_text()[:8000]
        except (OSError, UnicodeDecodeError):
            return ""
        return ""
