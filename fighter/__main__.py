from __future__ import annotations

import argparse
from pathlib import Path

from fighter.agent import Agent
from fighter.server import serve


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Busan Coder — Grok coding agent")
    ap.add_argument("--name", default="Busan Coder", help="agent name / identity")
    ap.add_argument("--callsign", default="BUSAN", help="talk-bubble callsign")
    ap.add_argument("--workspace", default=".", help="workspace root")
    ap.add_argument("--instructions", default="", help="extra system prompt")
    ap.add_argument("--model", default=None)
    ap.add_argument("--effort", default=None, choices=["low", "medium", "high"])
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args(argv)
    agent = Agent(
        args.name,
        callsign=args.callsign,
        workspace=Path(args.workspace).resolve(),
        extra_instructions=args.instructions,
        model=args.model,
        effort=args.effort,
    )
    agent.config.host = args.host
    agent.config.port = args.port
    agent.config.open_browser = not args.no_browser
    return serve(agent)


if __name__ == "__main__":
    raise SystemExit(main())
