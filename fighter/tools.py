from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

MAX_READ = 50 * 1024
MAX_BASH = 20_000

HandlerFn = Callable[[dict[str, Any]], str]


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: HandlerFn
    kind: str = "generic"  # read | write | edit | bash | generic

    def schema(self) -> dict[str, Any]:
        params = dict(self.parameters)
        params.setdefault("type", "object")
        params.setdefault("additionalProperties", False)
        return {
            "type": "function",
            "name": self.name,
            "description": self.description,
            "parameters": params,
        }


def tool(
    name: str | None = None,
    description: str = "",
    parameters: dict[str, Any] | None = None,
    kind: str = "generic",
) -> Callable[[HandlerFn], Tool]:
    """Decorator: turn a function(args: dict) -> str into a Tool."""

    def wrap(fn: HandlerFn) -> Tool:
        return Tool(
            name=name or fn.__name__,
            description=description or (fn.__doc__ or fn.__name__).strip(),
            parameters=parameters or {"type": "object", "properties": {}, "required": []},
            handler=fn,
            kind=kind,
        )

    return wrap


def resolve_path(workspace: Path, path: str) -> Path:
    p = Path(path).expanduser()
    if not p.is_absolute():
        p = workspace / p
    return p.resolve()


def tool_path(args: dict[str, Any]) -> str:
    for key in ("path", "file", "filename", "filepath", "file_path"):
        v = args.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def write_body(args: dict[str, Any]) -> str:
    for key in ("content", "contents", "text", "body"):
        v = args.get(key)
        if isinstance(v, str):
            return v
    return ""


def ungutter(detail: str) -> str:
    lines = []
    for line in detail.splitlines():
        if "\t" in line:
            num, rest = line.split("\t", 1)
            if num.strip().isdigit():
                lines.append(rest)
                continue
        lines.append(line)
    return "\n".join(lines)


def clip(s: str, n: int) -> str:
    if len(s) <= n:
        return s
    return s[:n] + "\n... (truncated)"


def builtin_tools(workspace: Path) -> list[Tool]:
    ws = workspace

    def do_read(args: dict[str, Any]) -> str:
        path = resolve_path(ws, tool_path(args) or str(args.get("path") or ""))
        if path.is_dir():
            names = []
            for ent in sorted(path.iterdir(), key=lambda e: e.name.lower()):
                names.append(ent.name + ("/" if ent.is_dir() else ""))
            return "\n".join(names) or "(empty directory)"
        data = path.read_bytes()
        if b"\x00" in data[:4096]:
            return f"(binary file: {path.name}, {len(data)} bytes)"
        text = data.decode("utf-8")
        lines = text.splitlines()
        start = int(args.get("offset") or 0)
        want = int(args.get("limit") or 500)
        width = max(len(str(start + want)), 1)
        out = []
        size = 0
        for i, line in enumerate(lines):
            if i < start:
                continue
            if i >= start + want:
                break
            row = f"{i + 1:>{width}}\t{line}\n"
            size += len(row)
            if size > MAX_READ:
                out.append(f"... (truncated at 50KB; offset={i})\n")
                break
            out.append(row)
        return "".join(out) or "(empty)"

    def do_write(args: dict[str, Any]) -> str:
        path = resolve_path(ws, tool_path(args) or str(args.get("path") or ""))
        path.parent.mkdir(parents=True, exist_ok=True)
        content = write_body(args)
        path.write_text(content)
        return f"wrote {path} ({len(content)} bytes)"

    def do_edit(args: dict[str, Any]) -> str:
        path = resolve_path(ws, str(args.get("path") or ""))
        old, new = str(args.get("old") or ""), str(args.get("new") or "")
        if not old:
            raise ValueError("`old` must not be empty")
        text = path.read_text()
        n = text.count(old)
        if n != 1:
            raise ValueError(f"`old` must appear exactly once (found {n})")
        path.write_text(text.replace(old, new, 1))
        return f"edited {path}"

    def do_bash(args: dict[str, Any]) -> str:
        cmd = str(args.get("cmd") or "")
        timeout = int(args.get("timeout") or 30)
        timeout = max(1, min(timeout, 600))
        p = subprocess.run(
            ["/bin/sh", "-c", cmd],
            cwd=ws,
            capture_output=True,
            timeout=timeout,
            stdin=subprocess.DEVNULL,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
        )
        text = (p.stdout + p.stderr).decode("utf-8", "replace")
        text = clip(text, MAX_BASH) or "(no output)"
        if p.returncode != 0:
            raise RuntimeError(f"exit {p.returncode}: {text}")
        return text

    return [
        Tool(
            "read",
            "Read a file. Absolute paths and paths outside the workspace are allowed. A directory lists names. Lines are numbered for display only — never copy those numbers into edit/write. Binary files (including PNG) return type/size instead of failing UTF-8.",
            {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"},
                    "offset": {"type": "integer", "description": "0-based start line"},
                    "limit": {"type": "integer", "description": "Max lines (default 500)"},
                },
                "required": ["path"],
                "additionalProperties": False,
            },
            do_read,
            kind="read",
        ),
        Tool(
            "write",
            "Create or overwrite a file. Absolute paths and paths outside the workspace are allowed.",
            {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"},
                    "content": {"type": "string", "description": "Full contents"},
                },
                "required": ["path", "content"],
                "additionalProperties": False,
            },
            do_write,
            kind="write",
        ),
        Tool(
            "edit",
            "Replace `old` with `new`. `old` must appear exactly once. Absolute paths and paths outside the workspace are allowed.",
            {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"},
                    "old": {"type": "string", "description": "Exact text to find"},
                    "new": {"type": "string", "description": "Replacement"},
                },
                "required": ["path", "old", "new"],
                "additionalProperties": False,
            },
            do_edit,
            kind="edit",
        ),
        Tool(
            "bash",
            "Run a shell command in the workspace. Combined stdout+stderr, capped at 20KB. Times out after 30s; pass timeout (seconds, max 600) for longer commands.",
            {
                "type": "object",
                "properties": {
                    "cmd": {"type": "string", "description": "Shell command"},
                    "timeout": {"type": "integer", "description": "Seconds before kill (default 30, max 600)"},
                },
                "required": ["cmd"],
                "additionalProperties": False,
            },
            do_bash,
            kind="bash",
        ),
    ]


def file_preview(workspace: Path, name: str, args: dict[str, Any], detail: str) -> str | None:
    if name == "write":
        return write_body(args)[:8000]
    if name == "read" and detail:
        if detail.startswith("(binary file:"):
            return detail[:8000]
        return ungutter(detail)[:8000]
    path = tool_path(args)
    if not path:
        return ungutter(detail)[:8000] if detail else None
    p = resolve_path(workspace, path)
    try:
        if p.is_file():
            return p.read_text()[:8000]
        if p.is_dir():
            return (detail or "")[:8000]
    except (OSError, UnicodeDecodeError):
        pass
    return ungutter(detail)[:8000] if detail else None
