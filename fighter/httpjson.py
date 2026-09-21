from __future__ import annotations

import json
import ssl
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

CTX = ssl.create_default_context()


def http_json(
    url: str,
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
    method: str | None = None,
) -> tuple[int, Any]:
    req = Request(url, data=data, method=method or ("POST" if data is not None else "GET"))
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urlopen(req, timeout=30, context=CTX) as resp:
            raw = resp.read()
            code = resp.getcode() or 200
    except HTTPError as e:
        raw = e.read()
        code = e.code
    text = raw.decode("utf-8", "replace")
    try:
        body = json.loads(text) if text else {}
    except json.JSONDecodeError:
        body = {"raw": text[:400]}
    return code, body
