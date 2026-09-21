#!/usr/bin/env python3
"""Record docs/demo.mp4 of a live LÖVE coding turn.

Agent workspace is /tmp/demo so the write/run stay off the repo.

Same idea as fun-coding-agent/scripts/record-demo.py: type a real task,
capture the live window (XGetImage), overlay the white-outline pointer,
and keep the mouse moving while the agent works.

    PYTHONPATH=$HOME/demo python3 scripts/record-demo.py
"""
from __future__ import annotations

import json
import math
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOVE_DIR = ROOT / "love2d"
WS = Path(os.environ.get("BUSAN_WORKSPACE", "/tmp/demo"))
OUT = Path(os.environ.get("DEMO_OUT", str(ROOT / "docs" / "demo.mp4")))
TITLE = "Busan Coder"
FPS = int(os.environ.get("FPS", "15"))
MAX_SEC = float(os.environ.get("DURATION", "90"))
HOST = os.environ.get("BUSAN_HOST", "127.0.0.1")
PORT = int(os.environ.get("BUSAN_PORT", "8765"))
URL = os.environ.get("BUSAN_AGENT", f"http://{HOST}:{PORT}/")

PROMPT = "write a python script that says hi to causewaybay ai, then run it"

os.environ.setdefault("DISPLAY", ":0.0")
os.environ.setdefault("XAUTHORITY", str(Path.home() / ".Xauthority"))
os.environ.pop("BUSAN_DEMO", None)
sys.path[:0] = [str(Path.home() / "demo")]

from record.window import WindowRecord  # noqa: E402


def find_love() -> str:
    for name in ("love", "love.exe", "lovec"):
        p = shutil.which(name)
        if p:
            return p
    extras = [
        str(Path.home() / "Downloads/squashfs-root/bin/love"),
        "/usr/bin/love",
        "/usr/local/bin/love",
        "/opt/homebrew/bin/love",
        "/Applications/love.app/Contents/MacOS/love",
    ]
    for p in extras:
        if os.path.isfile(p) and os.access(p, os.X_OK):
            return p
    print("need LÖVE 11 on PATH", file=sys.stderr)
    sys.exit(1)


def stop(proc: subprocess.Popen | None) -> None:
    if proc is None or proc.poll() is not None:
        return
    proc.send_signal(signal.SIGTERM)
    try:
        proc.wait(timeout=4)
    except subprocess.TimeoutExpired:
        proc.kill()


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


def http_json(path: str, timeout: float = 3.0) -> dict:
    req = urllib.request.Request(URL.rstrip("/") + path, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return {}


def post(path: str, payload: dict | None = None, timeout: float = 8.0) -> dict:
    data = json.dumps(payload or {}).encode()
    req = urllib.request.Request(
        URL.rstrip("/") + path,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode()
            return json.loads(raw) if raw else {}
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError, ValueError):
        return {}


def prepare_workspace() -> None:
    WS.mkdir(parents=True, exist_ok=True)
    for p in WS.iterdir():
        if p.is_file() and p.suffix in {".py", ".txt", ".md"}:
            try:
                p.unlink()
            except OSError:
                pass


def kill_listener() -> None:
    subprocess.run(
        ["pkill", "-f", "python3 -m fighter"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    deadline = time.time() + 3
    while time.time() < deadline and port_open(HOST, PORT):
        time.sleep(0.1)


def ensure_fighter() -> subprocess.Popen[bytes] | None:
    if port_open(HOST, PORT):
        kill_listener()
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
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
            HOST,
            "--port",
            str(PORT),
            "--no-browser",
        ],
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    deadline = time.time() + 8
    while time.time() < deadline:
        if port_open(HOST, PORT):
            return proc
        if proc.poll() is not None:
            break
        time.sleep(0.15)
    return proc


def wait_ready(secs: float = 20.0) -> dict:
    deadline = time.time() + secs
    last: dict = {}
    while time.time() < deadline:
        last = http_json("/api/status")
        if last.get("logged_in"):
            return last
        time.sleep(0.3)
    print(f"fighter not logged in: {last}", file=sys.stderr)
    sys.exit(1)


def figure8(t: float, cx: float, cy: float, rx: float, ry: float) -> tuple[float, float]:
    return cx + rx * math.sin(t), cy + ry * math.sin(2 * t) * 0.55


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    prepare_workspace()
    love = find_love()
    subprocess.run(
        ["pkill", "-f", f"{love} {LOVE_DIR}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    time.sleep(0.25)
    fighter = ensure_fighter()
    wait_ready()
    post("/api/new")
    time.sleep(0.3)
    env = os.environ.copy()
    env.pop("BUSAN_DEMO", None)
    env["BUSAN_AGENT"] = URL
    proc = subprocess.Popen(
        [love, str(LOVE_DIR)],
        cwd=str(LOVE_DIR),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        with WindowRecord(
            TITLE,
            OUT,
            fps=FPS,
            max_sec=MAX_SEC + 8,
            min_w=640,
            min_h=360,
            hide_cursor=True,
            overlay_pointer=True,
        ) as rec:
            rec.hold(0.6)
            rec.focus()
            rec.click(90, 690)
            rec.hold(0.25)
            rec.type_text(PROMPT, delay=0.04)
            rec.hold(0.4)
            rec.key("Return")
            rec.hold(0.5)
            t0 = time.monotonic()
            idle = 0.0
            saw_busy = False
            while time.monotonic() - t0 < MAX_SEC:
                u = (time.monotonic() - t0) * 0.55
                x, y = figure8(u, 640, 340, 260, 100)
                rec.move(x, y)
                st = http_json("/api/status")
                busy = bool(st.get("busy"))
                if busy:
                    idle = 0.0
                    saw_busy = True
                elif saw_busy:
                    idle += 0.12
                    # pad dwell + bash shot, then cut
                    if idle >= 4.0:
                        rec.hold(0.6)
                        break
                time.sleep(0.12)
            if not saw_busy:
                print("agent never went busy — keys may have missed the composer", file=sys.stderr)
        if not OUT.is_file() or OUT.stat().st_size < 1000:
            print("demo.mp4 missing or tiny", file=sys.stderr)
            return 1
        print(OUT, OUT.stat().st_size)
        return 0
    finally:
        stop(proc)
        if fighter is not None:
            stop(fighter)


if __name__ == "__main__":
    raise SystemExit(main())
