#!/usr/bin/env python3
"""Compatibility shim — the agent lives in `fighter/`."""
from __future__ import annotations

from fighter import Agent
from fighter.server import RECORD_DONE, serve as _serve, set_record_queue
from fighter.server import make_httpd as _make_httpd

__all__ = ["RECORD_DONE", "make_httpd", "serve", "set_record_queue"]


def _demo_agent() -> Agent:
    return Agent("Busan Coder", callsign="BUSAN")


def make_httpd(host: str = "127.0.0.1", port: int = 8765):
    return _make_httpd(_demo_agent(), host, port)


def serve(host: str = "127.0.0.1", port: int = 8765, open_browser: bool = True) -> int:
    return _serve(_demo_agent(), host, port, open_browser)


if __name__ == "__main__":
    raise SystemExit(serve())
