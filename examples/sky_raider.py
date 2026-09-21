#!/usr/bin/env python3
"""Example: a named fighter coding agent on this workspace."""
from pathlib import Path

from fighter import Agent, serve, tool

ROOT = Path(__file__).resolve().parents[1]


@tool(
    "ls",
    "List files in a directory under the workspace.",
    {
        "type": "object",
        "properties": {"path": {"type": "string", "description": "Directory path"}},
        "required": ["path"],
        "additionalProperties": False,
    },
    kind="read",
)
def ls(args: dict) -> str:
    from fighter.tools import resolve_path

    p = resolve_path(ROOT, str(args.get("path") or "."))
    if not p.is_dir():
        raise ValueError(f"not a directory: {p}")
    names = [e.name + ("/" if e.is_dir() else "") for e in sorted(p.iterdir(), key=lambda x: x.name.lower())]
    return "\n".join(names) or "(empty)"


def main() -> int:
    agent = Agent(
        "Sky Raider",
        callsign="RAIDER",
        workspace=ROOT,
        extra_instructions="You fly a coding fighter. Short replies. Fix, then verify.",
        extra_tools=[ls],
    )
    return serve(agent)


if __name__ == "__main__":
    raise SystemExit(main())
