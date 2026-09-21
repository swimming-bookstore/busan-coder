#!/usr/bin/env python3
"""Launch the LÖVE pad as a live fighter coding agent.

    python3 love2d/run.py
    love love2d

Starts `python3 -m fighter` if nothing is listening on the pad port.
"""
from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WS = ROOT.parent


def find_love() -> str | None:
    for name in ("love", "love.exe", "lovec"):
        p = shutil.which(name)
        if p:
            return p
    extras = [
        "/usr/bin/love",
        "/usr/local/bin/love",
        "/opt/homebrew/bin/love",
        "/Applications/love.app/Contents/MacOS/love",
        str(Path.home() / "Downloads/squashfs-root/bin/love"),
    ]
    for p in extras:
        if os.path.isfile(p) and os.access(p, os.X_OK):
            return p
    return None


def port_open(host: str, port: int) -> bool:
    s = socket.socket()
    s.settimeout(0.3)
    try:
        s.connect((host, port))
        return True
    except OSError:
        return False
    finally:
        s.close()


def ensure_fighter(host: str, port: int) -> subprocess.Popen[bytes] | None:
    if port_open(host, port):
        return None
    env = os.environ.copy()
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "fighter",
            "--name",
            "Busan Coder",
            "--callsign",
            "BUSAN",
            "--workspace",
            str(WS),
            "--host",
            host,
            "--port",
            str(port),
            "--no-browser",
        ],
        cwd=str(WS),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    deadline = time.time() + 5
    while time.time() < deadline:
        if port_open(host, port):
            return proc
        if proc.poll() is not None:
            break
        time.sleep(0.1)
    return proc


def main() -> int:
    love = find_love()
    if not love:
        print("need LÖVE 11 on PATH: https://love2d.org/", file=sys.stderr)
        return 1
    host = os.environ.get("BUSAN_HOST", "127.0.0.1")
    port = int(os.environ.get("BUSAN_PORT", "8765"))
    url = os.environ.get("BUSAN_AGENT", f"http://{host}:{port}/")
    child = ensure_fighter(host, port)
    env = os.environ.copy()
    env["BUSAN_AGENT"] = url
    try:
        return subprocess.call([love, str(ROOT), *sys.argv[1:]], env=env)
    finally:
        if child is not None and child.poll() is None:
            child.terminate()


if __name__ == "__main__":
    raise SystemExit(main())
