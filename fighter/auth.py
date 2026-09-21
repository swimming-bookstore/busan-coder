from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from fighter.httpjson import http_json

XAI_CLIENT_ID = "b1a00492-073a-47ea-816f-4c329264a828"
XAI_SCOPE = "openid profile email offline_access grok-cli:access api:access"
XAI_DEVICE_URL = "https://auth.x.ai/oauth2/device/code"
XAI_TOKEN_URL = "https://auth.x.ai/oauth2/token"


def default_auth_path() -> Path:
    return Path(os.environ.get("PROVIDER_GROK_AUTH") or Path.home() / ".local" / "share" / "fun" / "auth.json")


class AuthStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_auth_path()
        self.login: dict[str, Any] = {}

    def load(self) -> dict[str, Any] | None:
        try:
            t = json.loads(self.path.read_text())
        except (OSError, json.JSONDecodeError):
            return None
        if not t.get("access"):
            return None
        return t

    def save(self, t: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(f".auth.{os.getpid()}.tmp")
        tmp.write_text(json.dumps(t, indent=2) + "\n")
        tmp.chmod(0o600)
        tmp.replace(self.path)

    def clear(self) -> None:
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass
        self.login.clear()

    def refresh(self, refresh: str) -> dict[str, Any]:
        code, body = http_json(
            XAI_TOKEN_URL,
            urlencode(
                {
                    "grant_type": "refresh_token",
                    "client_id": XAI_CLIENT_ID,
                    "refresh_token": refresh,
                }
            ).encode(),
            {"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
        )
        if code >= 300:
            raise RuntimeError(body.get("error") or f"refresh HTTP {code}")
        access = body.get("access_token") or ""
        ref = body.get("refresh_token") or refresh
        life = int(body.get("expires_in") or 3600) * 1000
        skew = min(5 * 60 * 1000, max(0, life - 30_000))
        return {
            "access": access,
            "refresh": ref,
            "expires": int(time.time() * 1000) + life - skew,
        }

    def bearer(self) -> str:
        t = self.load()
        if not t:
            raise RuntimeError("not logged in — click login")
        now = int(time.time() * 1000)
        if now >= int(t.get("expires") or 0) and t.get("refresh"):
            t = self.refresh(t["refresh"])
            self.save(t)
        return str(t["access"])
