from __future__ import annotations

import json
import queue
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlencode

from fighter.agent import Agent
from fighter.auth import AuthStore, XAI_CLIENT_ID, XAI_DEVICE_URL, XAI_SCOPE, XAI_TOKEN_URL
from fighter.grok import grok_complete
from fighter.httpjson import http_json
from fighter.tools import tool_path

RECORD_Q: queue.Queue[bytes] | None = None
RECORD_DONE = threading.Event()


def set_record_queue(q: queue.Queue[bytes] | None) -> None:
    global RECORD_Q
    RECORD_Q = q
    RECORD_DONE.clear()


def sse_write(handler: BaseHTTPRequestHandler, event: str, data: Any) -> None:
    payload = json.dumps(data, ensure_ascii=False)
    handler.wfile.write(f"event: {event}\ndata: {payload}\n\n".encode())
    handler.wfile.flush()


class Runtime:
    def __init__(self, agent: Agent, auth: AuthStore | None = None) -> None:
        self.agent = agent
        self.auth = auth or AuthStore()
        self.abort = threading.Event()
        self.session: list[dict[str, Any]] = []
        self.usage = {"input": 0, "output": 0, "cached": 0, "reasoning": 0}
        self.chat_gen = 0
        self.busy = False

    def reset(self) -> None:
        self.abort.set()
        self.chat_gen += 1
        self.session.clear()
        self.usage = {"input": 0, "output": 0, "cached": 0, "reasoning": 0}
        self.busy = False

    def html_bytes(self) -> bytes:
        cfg = self.agent.config
        raw = cfg.html.read_text(encoding="utf-8")
        raw = raw.replace("__FIGHTER_NAME__", json.dumps(cfg.name)[1:-1])
        raw = raw.replace("__FIGHTER_CALLSIGN__", json.dumps(cfg.callsign)[1:-1])
        raw = raw.replace("__FIGHTER_RECORD_PROMPT__", json.dumps(cfg.record_prompt)[1:-1])
        return raw.encode("utf-8")

    def agent_turn(self, handler: BaseHTTPRequestHandler, text: str) -> None:
        gen = self.chat_gen
        self.abort.clear()
        self.busy = True
        try:
            self._agent_turn(handler, text, gen)
        finally:
            if self.chat_gen == gen:
                self.busy = False

    def _agent_turn(self, handler: BaseHTTPRequestHandler, text: str, gen: int) -> None:

        def alive() -> bool:
            return self.chat_gen == gen

        if not alive():
            return
        self.session.append({"kind": "user", "text": text})
        sse_write(handler, "user", {"text": text})
        for _ in range(self.agent.config.max_rounds):
            if not alive() or self.abort.is_set():
                if alive():
                    sse_write(handler, "dim", {"text": "(aborted)"})
                return

            def on_delta(d: str) -> None:
                if alive():
                    sse_write(handler, "delta", {"text": d})

            def on_think(d: str) -> None:
                if alive():
                    sse_write(handler, "think", {"text": d})

            try:
                reply = grok_complete(
                    self.agent,
                    self.session,
                    self.auth,
                    on_delta,
                    on_think,
                    alive,
                    self.abort.is_set,
                )
            except Exception as e:
                if alive():
                    sse_write(handler, "error", {"text": str(e)})
                return
            if not alive():
                return
            self.usage["input"] = reply.input_tokens
            self.usage["output"] = reply.output_tokens
            self.usage["cached"] = reply.cached_tokens
            self.usage["reasoning"] = reply.reasoning_tokens
            sse_write(
                handler,
                "usage",
                {
                    "input": reply.input_tokens,
                    "output": reply.output_tokens,
                    "cached": reply.cached_tokens,
                    "reasoning": reply.reasoning_tokens,
                },
            )
            if reply.truncated:
                sse_write(handler, "dim", {"text": "(truncated; tool calls dropped)"})
                if alive():
                    self.session.append({"kind": "assistant", "text": reply.text, "calls": []})
                return
            if not alive():
                return
            self.session.append({"kind": "assistant", "text": reply.text, "calls": reply.calls})
            if not reply.calls:
                sse_write(handler, "end", {"text": reply.text})
                return
            for c in reply.calls:
                if not alive() or self.abort.is_set():
                    if alive():
                        sse_write(handler, "dim", {"text": "(aborted)"})
                    return
                args = c.get("args") or {}
                path = tool_path(args)
                name = (c.get("name") or "").strip().split(".")[-1].lower()
                edit_orig = ""
                if name == "edit" and path:
                    edit_orig = self.agent.edit_orig(args)
                    sse_write(
                        handler,
                        "open",
                        {
                            "path": str(path),
                            "preview": edit_orig,
                            "name": name,
                            "edit_old": str(args.get("old") or "")[:8000],
                            "edit_new": str(args.get("new") or "")[:8000],
                        },
                    )
                if not alive():
                    return
                detail, is_error, preview = self.agent.run_tool(c["name"], args)
                if not alive():
                    return
                payload = self.agent.tool_payload(c["name"], args, detail, is_error, preview)
                if name == "edit":
                    payload["edit_orig"] = edit_orig
                sse_write(handler, "tool", payload)
                self.session.append({"kind": "tool", "id": c["id"], "content": detail})
        sse_write(handler, "dim", {"text": "(stopped after too many tool rounds)"})


def make_handler(rt: Runtime) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: Any) -> None:
            msg = fmt % args
            if "/api/frame" in msg:
                return
            sys.stderr.write("%s - %s\n" % (self.address_string(), msg))

        def _send(self, code: int, body: bytes, ctype: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, code: int, obj: Any) -> None:
            raw = json.dumps(obj).encode()
            self._send(code, raw, "application/json; charset=utf-8")

        def _read_json(self) -> dict[str, Any]:
            n = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(n) if n else b"{}"
            try:
                v = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                return {}
            return v if isinstance(v, dict) else {}

        def do_GET(self) -> None:
            path = self.path.split("?", 1)[0]
            if path in ("/", "/index.html", "/pad.html"):
                self._send(200, rt.html_bytes(), "text/html; charset=utf-8")
                return
            if path == "/api/status":
                t = rt.auth.load()
                self._json(
                    200,
                    {
                        "logged_in": bool(t),
                        "model": rt.agent.config.model,
                        "effort": rt.agent.effort(),
                        "workspace": str(rt.agent.config.workspace),
                        "usage": rt.usage,
                        "messages": len(rt.session),
                        "name": rt.agent.config.name,
                        "turns": sum(1 for m in rt.session if m.get("kind") == "user"),
                        "busy": bool(rt.busy),
                    },
                )
                return
            self._send(404, b"not found", "text/plain")

        def do_POST(self) -> None:
            path = self.path.split("?", 1)[0]
            if path == "/api/frame":
                n = int(self.headers.get("Content-Length") or 0)
                data = self.rfile.read(n) if n else b""
                if RECORD_Q is not None:
                    RECORD_Q.put(data)
                self._send(200, b"ok", "text/plain")
                return
            if path == "/api/record-done":
                RECORD_DONE.set()
                self._send(200, b"ok", "text/plain")
                return
            if path == "/api/abort":
                rt.abort.set()
                self._json(200, {"ok": True})
                return
            if path == "/api/new":
                rt.reset()
                self._json(200, {"ok": True})
                return
            if path == "/api/logout":
                rt.auth.clear()
                self._json(200, {"ok": True, "logged_in": False})
                return
            if path == "/api/login/start":
                code, body = http_json(
                    XAI_DEVICE_URL,
                    urlencode(
                        {
                            "client_id": XAI_CLIENT_ID,
                            "scope": XAI_SCOPE,
                            "referrer": "connect",
                        }
                    ).encode(),
                    {"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
                )
                if code >= 300:
                    self._json(400, {"error": body.get("error") or str(body)})
                    return
                rt.auth.login.clear()
                rt.auth.login.update(
                    {
                        "device_code": body.get("device_code"),
                        "interval": body.get("interval") or 5,
                        "deadline": time.time() + int(body.get("expires_in") or 900),
                    }
                )
                self._json(
                    200,
                    {
                        "user_code": body.get("user_code"),
                        "verification_uri": body.get("verification_uri"),
                        "verification_uri_complete": body.get("verification_uri_complete")
                        or body.get("verification_uri"),
                    },
                )
                return
            if path == "/api/login/poll":
                if not rt.auth.login.get("device_code"):
                    self._json(400, {"status": "idle"})
                    return
                code, body = http_json(
                    XAI_TOKEN_URL,
                    urlencode(
                        {
                            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                            "client_id": XAI_CLIENT_ID,
                            "device_code": rt.auth.login["device_code"],
                        }
                    ).encode(),
                    {"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
                )
                if 200 <= code < 300 and body.get("access_token"):
                    life = int(body.get("expires_in") or 3600) * 1000
                    skew = min(5 * 60 * 1000, max(0, life - 30_000))
                    rt.auth.save(
                        {
                            "access": body["access_token"],
                            "refresh": body.get("refresh_token") or "",
                            "expires": int(time.time() * 1000) + life - skew,
                        }
                    )
                    rt.auth.login.clear()
                    self._json(200, {"status": "done"})
                    return
                err = body.get("error") or ""
                if err == "authorization_pending":
                    self._json(200, {"status": "pending"})
                elif err == "slow_down":
                    self._json(200, {"status": "pending"})
                elif err in ("access_denied", "authorization_denied"):
                    self._json(200, {"status": "denied"})
                elif err == "expired_token":
                    self._json(200, {"status": "expired"})
                else:
                    self._json(200, {"status": "error", "error": err or f"HTTP {code}"})
                return
            if path == "/api/turn":
                body = self._read_json()
                text = str(body.get("text") or "").strip()
                if not text:
                    self._json(400, {"error": "empty"})
                    return
                if not rt.auth.load():
                    self._json(401, {"error": "not logged in — click login"})
                    return
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Accel-Buffering", "no")
                self.end_headers()
                try:
                    rt.agent_turn(self, text)
                except BrokenPipeError:
                    rt.abort.set()
                return
            self._send(404, b"not found", "text/plain")

    return Handler


def make_httpd(agent: Agent, host: str | None = None, port: int | None = None) -> tuple[ThreadingHTTPServer, int]:
    cfg = agent.config
    host = host or cfg.host
    port = port or cfg.port
    handler = make_handler(Runtime(agent))
    last: OSError | None = None
    for p in range(port, port + 8):
        try:
            return ThreadingHTTPServer((host, p), handler), p
        except OSError as e:
            last = e
    raise OSError(f"bind failed ({last})")


def serve(
    agent: Agent | None = None,
    host: str | None = None,
    port: int | None = None,
    open_browser: bool | None = None,
) -> int:
    agent = agent or Agent()
    cfg = agent.config
    if not cfg.html.is_file():
        print(f"missing {cfg.html}", file=sys.stderr)
        return 1
    try:
        httpd, bound = make_httpd(agent, host or cfg.host, port or cfg.port)
    except OSError as e:
        print(e, file=sys.stderr)
        return 1
    h = host or cfg.host
    url = f"http://{h}:{bound}/"
    print(url)
    print(f"fighter {cfg.name}")
    print(f"workspace {cfg.workspace}")
    print(f"auth {AuthStore().path}  logged_in={bool(AuthStore().load())}")
    if open_browser if open_browser is not None else cfg.open_browser:
        webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")
    finally:
        httpd.server_close()
    return 0
