#!/usr/bin/env python3
"""
Live UI is raid_demo.html (Grok + tools). Same page for play and record.

    python3 raid_demo.py
    python3 raid_demo.py --record
    python3 raid_demo.py --out /tmp/raid.mp4

Needs Python 3.10+. Live play needs a browser. Recording needs Chromium + ffmpeg.
"""
from __future__ import annotations

import argparse
import math
import shutil
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

W, H = 1280, 720
FPS = 30
DT = 1 / FPS

VOID = (8, 48, 84)
NAVY = (12, 72, 112)
SKY_RUST = (248, 152, 56)
SKY_GO = (80, 216, 248)
SKY_CPP = (120, 168, 248)
SKY_PY = (248, 208, 56)
COIN = (248, 208, 48)
CYAN = (80, 216, 248)
PINK = (248, 120, 168)
CREAM = (252, 236, 200)
INK = (32, 20, 12)
GRASS = (72, 200, 88)
BRICK = (216, 84, 24)
PANEL = (248, 208, 136)
DIM = (132, 116, 100)
GUTTER = (10, 44, 68)
WELL = (6, 28, 48)
WHITE = (255, 255, 255)

# 8×8 ISO-ish face. Each glyph is 8 row bytes, MSB = left pixel.
def _rows(*lines: str) -> tuple[int, ...]:
    out = []
    for line in lines:
        bits = 0
        for i, ch in enumerate(line[:8].ljust(8)):
            if ch not in " .":
                bits |= 1 << (7 - i)
        out.append(bits)
    while len(out) < 8:
        out.append(0)
    return tuple(out)


_FONT: dict[str, tuple[int, ...]] = {
    " ": _rows("        "),
    "A": _rows("  ####  ", " ##  ## ", " ##  ## ", " ###### ", " ##  ## ", " ##  ## ", " ##  ## "),
    "B": _rows(" #####  ", " ##  ## ", " ##  ## ", " #####  ", " ##  ## ", " ##  ## ", " #####  "),
    "C": _rows("  ##### ", " ##     ", " ##     ", " ##     ", " ##     ", " ##     ", "  ##### "),
    "D": _rows(" #####  ", " ##  ## ", " ##  ## ", " ##  ## ", " ##  ## ", " ##  ## ", " #####  "),
    "E": _rows(" ###### ", " ##     ", " ##     ", " #####  ", " ##     ", " ##     ", " ###### "),
    "F": _rows(" ###### ", " ##     ", " ##     ", " #####  ", " ##     ", " ##     ", " ##     "),
    "G": _rows("  ##### ", " ##     ", " ##     ", " ## ### ", " ##  ## ", " ##  ## ", "  ##### "),
    "H": _rows(" ##  ## ", " ##  ## ", " ##  ## ", " ###### ", " ##  ## ", " ##  ## ", " ##  ## "),
    "I": _rows("  ####  ", "   ##   ", "   ##   ", "   ##   ", "   ##   ", "   ##   ", "  ####  "),
    "J": _rows("   #### ", "    ##  ", "    ##  ", "    ##  ", "    ##  ", " ## ##  ", "  ###   "),
    "K": _rows(" ##  ## ", " ## ##  ", " ####   ", " ###    ", " ####   ", " ## ##  ", " ##  ## "),
    "L": _rows(" ##     ", " ##     ", " ##     ", " ##     ", " ##     ", " ##     ", " ###### "),
    "M": _rows(" ##   ##", " ### ###", " #######", " ## # ##", " ##   ##", " ##   ##", " ##   ##"),
    "N": _rows(" ##  ## ", " ### ## ", " ###### ", " ## ### ", " ##  ## ", " ##  ## ", " ##  ## "),
    "O": _rows("  ####  ", " ##  ## ", " ##  ## ", " ##  ## ", " ##  ## ", " ##  ## ", "  ####  "),
    "P": _rows(" #####  ", " ##  ## ", " ##  ## ", " #####  ", " ##     ", " ##     ", " ##     "),
    "Q": _rows("  ####  ", " ##  ## ", " ##  ## ", " ##  ## ", " ## ### ", " ##  ## ", "  ##### "),
    "R": _rows(" #####  ", " ##  ## ", " ##  ## ", " #####  ", " ## ##  ", " ##  ## ", " ##  ## "),
    "S": _rows("  ##### ", " ##     ", " ##     ", "  ####  ", "     ## ", "     ## ", " #####  "),
    "T": _rows(" ###### ", "   ##   ", "   ##   ", "   ##   ", "   ##   ", "   ##   ", "   ##   "),
    "U": _rows(" ##  ## ", " ##  ## ", " ##  ## ", " ##  ## ", " ##  ## ", " ##  ## ", "  ####  "),
    "V": _rows(" ##  ## ", " ##  ## ", " ##  ## ", " ##  ## ", " ##  ## ", "  ####  ", "   ##   "),
    "W": _rows(" ##   ##", " ##   ##", " ##   ##", " ## # ##", " #######", " ### ###", " ##   ##"),
    "X": _rows(" ##  ## ", " ##  ## ", "  ####  ", "   ##   ", "  ####  ", " ##  ## ", " ##  ## "),
    "Y": _rows(" ##  ## ", " ##  ## ", "  ####  ", "   ##   ", "   ##   ", "   ##   ", "   ##   "),
    "Z": _rows(" ###### ", "     ## ", "    ##  ", "   ##   ", "  ##    ", " ##     ", " ###### "),
    "a": _rows("        ", "  ####  ", "     ## ", "  ##### ", " ##  ## ", " ##  ## ", "  ##### "),
    "b": _rows(" ##     ", " ##     ", " #####  ", " ##  ## ", " ##  ## ", " ##  ## ", " #####  "),
    "c": _rows("        ", "  ####  ", " ##     ", " ##     ", " ##     ", " ##     ", "  ####  "),
    "d": _rows("     ## ", "     ## ", "  ##### ", " ##  ## ", " ##  ## ", " ##  ## ", "  ##### "),
    "e": _rows("        ", "  ####  ", " ##  ## ", " ###### ", " ##     ", " ##     ", "  ####  "),
    "f": _rows("   ###  ", "  ##    ", " ###### ", "  ##    ", "  ##    ", "  ##    ", "  ##    "),
    "g": _rows("        ", "  ##### ", " ##  ## ", " ##  ## ", "  ##### ", "     ## ", "  ####  "),
    "h": _rows(" ##     ", " ##     ", " #####  ", " ##  ## ", " ##  ## ", " ##  ## ", " ##  ## "),
    "i": _rows("   ##   ", "        ", "  ###   ", "   ##   ", "   ##   ", "   ##   ", "  ####  "),
    "j": _rows("    ##  ", "        ", "   ###  ", "    ##  ", "    ##  ", " ## ##  ", "  ###   "),
    "k": _rows(" ##     ", " ##     ", " ## ##  ", " ####   ", " ## ##  ", " ##  ## ", " ##  ## "),
    "l": _rows("  ###   ", "   ##   ", "   ##   ", "   ##   ", "   ##   ", "   ##   ", "  ####  "),
    "m": _rows("        ", " ## ##  ", " #######", " ## # ##", " ## # ##", " ##   ##", " ##   ##"),
    "n": _rows("        ", " #####  ", " ##  ## ", " ##  ## ", " ##  ## ", " ##  ## ", " ##  ## "),
    "o": _rows("        ", "  ####  ", " ##  ## ", " ##  ## ", " ##  ## ", " ##  ## ", "  ####  "),
    "p": _rows("        ", " #####  ", " ##  ## ", " ##  ## ", " #####  ", " ##     ", " ##     "),
    "q": _rows("        ", "  ##### ", " ##  ## ", " ##  ## ", "  ##### ", "     ## ", "     ## "),
    "r": _rows("        ", " ## ### ", " ###    ", " ##     ", " ##     ", " ##     ", " ##     "),
    "s": _rows("        ", "  ##### ", " ##     ", "  ####  ", "     ## ", "     ## ", " #####  "),
    "t": _rows("  ##    ", "  ##    ", " ###### ", "  ##    ", "  ##    ", "  ##    ", "   ###  "),
    "u": _rows("        ", " ##  ## ", " ##  ## ", " ##  ## ", " ##  ## ", " ##  ## ", "  ##### "),
    "v": _rows("        ", " ##  ## ", " ##  ## ", " ##  ## ", " ##  ## ", "  ####  ", "   ##   "),
    "w": _rows("        ", " ##   ##", " ## # ##", " ## # ##", " #######", " ### ###", " ##   ##"),
    "x": _rows("        ", " ##  ## ", "  ####  ", "   ##   ", "  ####  ", " ##  ## ", " ##  ## "),
    "y": _rows("        ", " ##  ## ", " ##  ## ", " ##  ## ", "  ##### ", "     ## ", "  ####  "),
    "z": _rows("        ", " ###### ", "    ##  ", "   ##   ", "  ##    ", " ##     ", " ###### "),
    "0": _rows("  ####  ", " ##  ## ", " ## ### ", " ### ## ", " ##  ## ", " ##  ## ", "  ####  "),
    "1": _rows("   ##   ", "  ###   ", "   ##   ", "   ##   ", "   ##   ", "   ##   ", "  ####  "),
    "2": _rows("  ####  ", " ##  ## ", "     ## ", "   ###  ", "  ##    ", " ##     ", " ###### "),
    "3": _rows("  ####  ", " ##  ## ", "     ## ", "   ###  ", "     ## ", " ##  ## ", "  ####  "),
    "4": _rows("    ##  ", "   ###  ", "  # ##  ", " ## ##  ", " ###### ", "    ##  ", "    ##  "),
    "5": _rows(" ###### ", " ##     ", " #####  ", "     ## ", "     ## ", " ##  ## ", "  ####  "),
    "6": _rows("  ####  ", " ##     ", " #####  ", " ##  ## ", " ##  ## ", " ##  ## ", "  ####  "),
    "7": _rows(" ###### ", "     ## ", "    ##  ", "   ##   ", "  ##    ", "  ##    ", "  ##    "),
    "8": _rows("  ####  ", " ##  ## ", " ##  ## ", "  ####  ", " ##  ## ", " ##  ## ", "  ####  "),
    "9": _rows("  ####  ", " ##  ## ", " ##  ## ", "  ##### ", "     ## ", "     ## ", "  ####  "),
    ".": _rows("        ", "        ", "        ", "        ", "        ", "  ##    ", "  ##    "),
    ",": _rows("        ", "        ", "        ", "        ", "        ", "  ##    ", "  ##    ", " ##     "),
    ":": _rows("        ", "  ##    ", "  ##    ", "        ", "  ##    ", "  ##    "),
    ";": _rows("        ", "  ##    ", "  ##    ", "        ", "  ##    ", "  ##    ", " ##     "),
    ";": _rows("        ", "  ##    ", "  ##    ", "        ", "  ##    ", "  ##    ", " ##     "),
    "!": _rows("  ##    ", "  ##    ", "  ##    ", "  ##    ", "  ##    ", "        ", "  ##    "),
    "?": _rows("  ####  ", " ##  ## ", "     ## ", "   ###  ", "   ##   ", "        ", "   ##   "),
    "-": _rows("        ", "        ", "        ", " ###### ", "        ", "        "),
    "_": _rows("        ", "        ", "        ", "        ", "        ", "        ", " ###### "),
    "+": _rows("        ", "   ##   ", "   ##   ", " ###### ", "   ##   ", "   ##   "),
    "=": _rows("        ", "        ", " ###### ", "        ", " ###### ", "        "),
    "(": _rows("    ##  ", "   ##   ", "  ##    ", "  ##    ", "  ##    ", "   ##   ", "    ##  "),
    ")": _rows("  ##    ", "   ##   ", "    ##  ", "    ##  ", "    ##  ", "   ##   ", "  ##    "),
    "[": _rows("  ####  ", "  ##    ", "  ##    ", "  ##    ", "  ##    ", "  ##    ", "  ####  "),
    "]": _rows("  ####  ", "    ##  ", "    ##  ", "    ##  ", "    ##  ", "    ##  ", "  ####  "),
    "{": _rows("    ### ", "   ##   ", "   ##   ", "  ##    ", "   ##   ", "   ##   ", "    ### "),
    "}": _rows(" ###    ", "   ##   ", "   ##   ", "    ##  ", "   ##   ", "   ##   ", " ###    "),
    "/": _rows("     ## ", "    ##  ", "    ##  ", "   ##   ", "  ##    ", "  ##    ", " ##     "),
    "\\": _rows(" ##     ", "  ##    ", "  ##    ", "   ##   ", "    ##  ", "    ##  ", "     ## "),
    "'": _rows("  ##    ", "  ##    ", " ##     "),
    '"': _rows(" ## ##  ", " ## ##  "),
    "`": _rows("  ##    ", "   ##   "),
    "*": _rows("        ", " ##  ## ", "  ####  ", " ###### ", "  ####  ", " ##  ## "),
    "#": _rows("  ## ## ", "  ## ## ", "####### ", "  ## ## ", "####### ", "  ## ## ", "  ## ## "),
    "$": _rows("   ##   ", "  ##### ", " ##     ", "  ####  ", "     ## ", " #####  ", "   ##   "),
    "%": _rows(" ##   ##", " ##  ## ", "    ##  ", "   ##   ", "  ##    ", " ##  ## ", "##   ## "),
    "&": _rows("  ###   ", " ## ##  ", "  ###   ", "  ##  # ", " ## ##  ", " ##  ## ", "  ##  ##"),
    "^": _rows("   ##   ", "  ####  ", " ##  ## "),
    "|": _rows("   ##   ", "   ##   ", "   ##   ", "   ##   ", "   ##   ", "   ##   ", "   ##   "),
    "<": _rows("    ##  ", "   ##   ", "  ##    ", " ##     ", "  ##    ", "   ##   ", "    ##  "),
    ">": _rows("  ##    ", "   ##   ", "    ##  ", "     ## ", "    ##  ", "   ##   ", "  ##    "),
    "~": _rows("        ", "        ", "  ##  ##", " ##  ## "),
    "@": _rows("  ####  ", " ##  ## ", " ## ### ", " ## # # ", " ## ### ", " ##     ", "  ####  "),
    "·": _rows("        ", "        ", "  ##    ", "  ##    "),
}


def glyph(ch: str) -> tuple[int, ...]:
    # Never draw "?" for a missing face: that is how a tab or a smart
    # quote became a question-mark at the start of the landed line.
    if ch == "\t":
        return _FONT[" "]
    return _FONT.get(ch) or _FONT.get(ch.upper()) or _FONT[" "]


def clamp(t: float, a: float = 0.0, b: float = 1.0) -> float:
    return a if t < a else b if t > b else t


def exp_in_out(t: float) -> float:
    t = clamp(t)
    if t < 0.5:
        return 0.5 * math.pow(2, 20 * t - 10)
    return 1 - 0.5 * math.pow(2, -20 * t + 10)


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def mix(c0: tuple[int, int, int], c1: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    t = clamp(t)
    return (
        int(lerp(c0[0], c1[0], t)),
        int(lerp(c0[1], c1[1], t)),
        int(lerp(c0[2], c1[2], t)),
    )


class Buf:
    def __init__(self, w: int, h: int) -> None:
        self.w, self.h = w, h
        self.pix = bytearray(w * h * 3)

    def fill(self, c: tuple[int, int, int]) -> None:
        self.pix[:] = bytes(c) * (self.w * self.h)

    def put(self, x: int, y: int, c: tuple[int, int, int], a: float = 1.0) -> None:
        if a <= 0 or x < 0 or y < 0 or x >= self.w or y >= self.h:
            return
        i = (y * self.w + x) * 3
        p = self.pix
        if a >= 1:
            p[i], p[i + 1], p[i + 2] = c
            return
        ia = 1.0 - a
        p[i] = int(p[i] * ia + c[0] * a)
        p[i + 1] = int(p[i + 1] * ia + c[1] * a)
        p[i + 2] = int(p[i + 2] * ia + c[2] * a)

    def rect(self, x: int, y: int, w: int, h: int, c: tuple[int, int, int], a: float = 1.0) -> None:
        x0 = max(0, int(x))
        y0 = max(0, int(y))
        x1 = min(self.w, int(x + w))
        y1 = min(self.h, int(y + h))
        if x1 <= x0 or y1 <= y0:
            return
        if a >= 1:
            row = bytes(c) * (x1 - x0)
            p = self.pix
            stride = self.w * 3
            for yy in range(y0, y1):
                i = yy * stride + x0 * 3
                p[i : i + len(row)] = row
            return
        for yy in range(y0, y1):
            for xx in range(x0, x1):
                self.put(xx, yy, c, a)

    def circle(self, cx: float, cy: float, r: float, c: tuple[int, int, int], a: float = 1.0, fill: bool = False) -> None:
        r2 = r * r
        x0 = max(0, int(cx - r - 1))
        y0 = max(0, int(cy - r - 1))
        x1 = min(self.w, int(cx + r + 2))
        y1 = min(self.h, int(cy + r + 2))
        band = 1.6
        for y in range(y0, y1):
            dy = y + 0.5 - cy
            for x in range(x0, x1):
                dx = x + 0.5 - cx
                d2 = dx * dx + dy * dy
                if fill:
                    if d2 <= r2:
                        self.put(x, y, c, a)
                else:
                    d = math.sqrt(d2)
                    gap = abs(d - r)
                    if gap < band:
                        self.put(x, y, c, a * (1 - gap / band))

    def diamond(self, cx: float, cy: float, r: float, c: tuple[int, int, int], a: float = 1.0) -> None:
        x0 = max(0, int(cx - r - 1))
        y0 = max(0, int(cy - r - 1))
        x1 = min(self.w, int(cx + r + 2))
        y1 = min(self.h, int(cy + r + 2))
        for y in range(y0, y1):
            for x in range(x0, x1):
                if abs(x - cx) / 0.7 + abs(y - cy) <= r:
                    self.put(x, y, c, a)

    def glow(self, cx: float, cy: float, r: float, c: tuple[int, int, int], a: float) -> None:
        x0 = max(0, int(cx - r))
        y0 = max(0, int(cy - r))
        x1 = min(self.w, int(cx + r + 1))
        y1 = min(self.h, int(cy + r + 1))
        r2 = r * r
        for y in range(y0, y1):
            dy = y + 0.5 - cy
            for x in range(x0, x1):
                dx = x + 0.5 - cx
                d2 = dx * dx + dy * dy
                if d2 >= r2:
                    continue
                k = 1.0 - math.sqrt(d2) / r
                self.put(x, y, c, a * k * k)

    def text(self, s: str, x: int, y: int, c: tuple[int, int, int], scale: int = 2, a: float = 1.0) -> int:
        ox = x
        for ch in s:
            bits = glyph(ch)
            for row, line in enumerate(bits):
                for col in range(8):
                    if line & (1 << (7 - col)):
                        self.rect(ox + col * scale, y + row * scale, scale, scale, c, a)
            ox += 8 * scale
        return ox - x

    def text_w(self, s: str, scale: int = 2) -> int:
        return len(s) * 8 * scale


def _rot(px: float, py: float, ca: float, sa: float, facing: int) -> tuple[float, float]:
    px *= facing
    return px * ca - py * sa, px * sa + py * ca


def draw_ship(buf: Buf, cx: float, cy: float, facing: int, scale: float, angle: float, pulse: float, hull: tuple[int, int, int]) -> None:
    """A nose-up fighter: body, wings, canopy, guns."""
    sx = 11 * scale * (1 + 0.14 * pulse)
    sy = 14 * scale * (1 - 0.14 * pulse)
    ca, sa = math.cos(angle), math.sin(angle)

    def put(px: float, py: float, w: float, h: float, c: tuple[int, int, int], a: float = 1.0) -> None:
        rx, ry = _rot(px, py, ca, sa, facing)
        buf.rect(int(cx + rx - w / 2), int(cy + ry - h / 2), int(max(1, w)), int(max(1, h)), c, a)

    # Glow
    buf.glow(cx, cy, sx * 1.8, hull, 0.22)
    # Wings
    put(0.72 * sx, 0.12 * sy, 0.55 * sx, 0.18 * sy, hull)
    put(-0.72 * sx, 0.12 * sy, 0.55 * sx, 0.18 * sy, hull)
    put(0.55 * sx, 0.08 * sy, 0.22 * sx, 0.1 * sy, CYAN)
    put(-0.55 * sx, 0.08 * sy, 0.22 * sx, 0.1 * sy, CYAN)
    # Twin guns
    put(0.38 * sx, -0.42 * sy, 0.1 * sx, 0.28 * sy, CREAM)
    put(-0.38 * sx, -0.42 * sy, 0.1 * sx, 0.28 * sy, CREAM)
    # Fuselage
    put(0, 0.05 * sy, 0.38 * sx, 0.95 * sy, hull)
    put(0, -0.05 * sy, 0.22 * sx, 0.7 * sy, CREAM)
    # Nose
    buf.diamond(cx + _rot(0, -0.55 * sy, ca, sa, facing)[0], cy + _rot(0, -0.55 * sy, ca, sa, facing)[1], 0.22 * sy, CYAN)
    # Canopy
    buf.diamond(cx, cy - 0.08 * sy, 0.16 * sy, WHITE, 0.9)
    # Tail fins
    put(0.18 * sx, 0.42 * sy, 0.12 * sx, 0.28 * sy, PINK)
    put(-0.18 * sx, 0.42 * sy, 0.12 * sx, 0.28 * sy, PINK)


class Shot:
    __slots__ = ("x", "y", "vx", "vy", "hx", "hy", "text", "age", "life", "color", "idx", "form", "kind", "col")

    def __init__(
        self,
        x: float,
        y: float,
        vx: float,
        vy: float,
        hx: float,
        hy: float,
        text: str,
        color: tuple[int, int, int],
        idx: int,
    ) -> None:
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.hx, self.hy = hx, hy
        self.text = text
        self.age = 0.0
        self.life = 1.7
        self.color = color
        self.idx = idx
        self.form = 0.0
        self.kind = "add"
        self.col = 0


class Thought:
    __slots__ = ("x", "y", "vx", "vy", "hx", "hy", "text", "age", "life", "color", "form", "phase")

    def __init__(
        self,
        x: float,
        y: float,
        vx: float,
        vy: float,
        hx: float,
        hy: float,
        text: str,
        color: tuple[int, int, int],
        phase: float,
    ) -> None:
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.hx, self.hy = hx, hy
        self.text = text
        self.age = 0.0
        self.life = 3.4
        self.color = color
        self.form = 0.0
        self.phase = phase


class Base:
    __slots__ = ("x", "y", "age", "life", "label")

    def __init__(self, x: float, y: float, label: str) -> None:
        self.x, self.y, self.label = x, y, label
        self.age = 0.0
        self.life = 2.6


# A longer job in demo/: read a bug, fail a test, edit, re-run, write a file.
SCORE_BUG = [
    "def total(scores):",
    "    n = 0",
    "    for s in scores:",
    "        n = n - s",
    "    return n",
]
SCORE_FIX = [
    "def total(scores):",
    "    n = 0",
    "    for s in scores:",
    "        n = n + s",
    "    return n",
]
SHELL_FAIL = [
    "$ python3 demo/test_score.py",
    "AssertionError",
    "-6 == 6",
]
SHELL_OK = [
    "$ python3 demo/test_score.py",
    "ok",
]
GREET = [
    "def greet(name):",
    '    return f"hello, {name}"',
    "",
    'if __name__ == "__main__":',
    '    print(greet("causewaybay"))',
]


def is_row(line: str, i: int, n: int) -> bool:
    """A trailing newline of the file is not a row; an interior blank is."""
    if i == n - 1 and not line:
        return False
    return True


def words_of(line: str) -> list[tuple[str, int]]:
    """Non-space tokens of a line, with the column each word starts at."""
    out: list[tuple[str, int]] = []
    col = None
    for i, ch in enumerate(line):
        if ch not in " \t":
            if col is None:
                col = i
        elif col is not None:
            out.append((line[col:i], col))
            col = None
    if col is not None:
        out.append((line[col:], col))
    return out


def payload_plan(empty: list[str], hello: list[str]) -> tuple[list[str], list[int], list[str], list[int]]:
    """Shoot only new words. Each word flies into its line and column."""
    left: dict[str, list[int]] = {}
    for i, line in enumerate(empty):
        if not is_row(line, i, len(empty)) or not line:
            continue
        left.setdefault(line, []).append(i)
    lines: list[str] = []
    aims: list[int] = []
    kinds: list[str] = []
    cols: list[int] = []

    def take(line: str, i: int, kind: str) -> None:
        for text, col in words_of(line):
            lines.append(text)
            aims.append(i)
            kinds.append(kind)
            cols.append(col)

    for i, line in enumerate(hello):
        if not is_row(line, i, len(hello)) or not line:
            continue
        at = left.get(line)
        if at:
            at.pop(0)
            continue
        # Same row as an add is a replace only if that old line is gone.
        # A shifted `}` still lives later and must not be consumed here.
        old = empty[i] if i < len(empty) else ""
        if old and old not in hello:
            old_at = left.get(old)
            if old_at and i in old_at:
                old_at.remove(i)
        take(line, i, "add")
    for i, line in enumerate(empty):
        if not is_row(line, i, len(empty)) or not line:
            continue
        at = left.get(line)
        if at and i in at:
            take(line, i, "cut")
    return lines, aims, kinds, cols


def align_pad(empty: list[str], hello: list[str]) -> list[str]:
    """Keep matching lines, open a hole at each new line's own number."""
    used: set[int] = set()
    out = [""] * max(len(hello), 1)
    for i, line in enumerate(hello):
        if not line.strip():
            continue
        for j, el in enumerate(empty):
            if j in used or el != line:
                continue
            out[i] = line
            used.add(j)
            break
    return out


class Demo:
    def __init__(self) -> None:
        self.t = 0.0
        self.x, self.y = 980.0, 420.0
        self.facing = -1
        self.angle = 0.0
        self.scale = 3.2
        self.pulse = 0.0
        self.state = "wander"
        self.phase = 0.0
        self.shots: list[Shot] = []
        self.thoughts: list[Thought] = []
        self.think_q: list[str] = []
        self.think_board: list[str] = []
        self.think_busy = False
        self.think_lift = 0.0
        self.think_hold = 0.0
        self.think_a = 0.0
        self.thinking = ""
        self.bases: list[Base] = []
        self.trail: list[tuple[float, float]] = []
        self.sky = SKY_PY
        self.sky_a = 0.0
        self.file = "score.py"
        self.lang = "PYTHON"
        self.tool = ""
        self.code: list[str] = list(SCORE_BUG)
        self.land_i = 0
        self.caption = ""
        self.flight: tuple[float, float, float, float, float, float] | None = None
        self.box = (72, 138, 1136, 420)
        self.caret = 0
        self.blink = 0.0
        self.applied: set[str] = set()
        self.read_path: list[tuple[float, float]] = []
        self.read_i = 0
        self.read_hold = 0.0
        self.talks: list[str] = []
        self.talk_i = 0
        self.talk_until = 0.0
        self.done: set[str] = set()
        self.scanlines = True
        self.beat = 22.0

    def go(self, tx: float, ty: float, secs: float) -> None:
        self.flight = (self.x, self.y, tx, ty, 0.0, secs)

    def line_xy(self, i: int, col: int = 0) -> tuple[float, float]:
        bx, by, _, _ = self.box
        # Whole line left-aligns on the well; indent lives in the text.
        return bx + 80.0 + col * 16.0, by + 56.0 + i * 36.0

    def fire(
        self,
        lines: list[str],
        aims: list[int],
        kinds: list[str],
        cols: list[int],
        color: tuple[int, int, int],
    ) -> None:
        # From under the hull into that word's line and column.
        speed = 360
        y0 = self.y + 36
        n = len(lines)
        for i, line in enumerate(lines):
            hx, hy = self.line_xy(aims[i] if i < len(aims) else 1, cols[i] if i < len(cols) else 0)
            dx, dy = hx - self.x, hy - y0
            dist = math.hypot(dx, dy) or 1
            ux, uy = dx / dist, dy / dist
            fan = 0.0 if n == 1 else (i / (n - 1) - 0.5) * 0.45
            shot = Shot(
                self.x,
                y0,
                (ux - uy * fan) * speed,
                (uy + ux * fan) * speed,
                hx,
                hy,
                line,
                color,
                aims[i] if i < len(aims) else i,
            )
            shot.kind = kinds[i] if i < len(kinds) else "add"
            shot.col = cols[i] if i < len(cols) else 0
            shot.life = max(2.4, dist / speed + 0.7)
            self.shots.append(shot)

    def think_well(self) -> tuple[float, float, float, float]:
        bx, by, bw, _bh = self.box
        th = 72.0
        return bx + 10, by - th - 8, max(80.0, bw - 20), th

    def talk_well(self) -> tuple[float, float, float, float]:
        bx, by, bw, bh = self.box
        th = 88.0
        return bx, by + bh + 8, bw, th

    def wrap_think(self, text: str) -> list[str]:
        wx, _wy, ww, _wh = self.think_well()
        width = max(8, int((ww - 24) / 16))
        out: list[str] = []
        rest = " ".join((text or "").split())
        while len(rest) > width:
            cut = rest.rfind(" ", 0, width)
            if cut < 8:
                cut = width
            out.append(rest[:cut].strip())
            rest = rest[cut:].strip()
        if rest:
            out.append(rest)
        return out

    def fire_next_thought(self) -> None:
        if self.think_busy or not self.think_q:
            return
        line = self.think_q.pop(0)
        wx, wy, ww, wh = self.think_well()
        x0 = self.x + self.facing * 18
        y0 = self.y - 26
        hx = wx + 10
        hy = wy + wh - 24
        dx, dy = hx - x0, hy - y0
        dist = math.hypot(dx, dy) or 1
        speed = 420
        self.thoughts.append(
            Thought(
                x0,
                y0,
                (dx / dist) * speed,
                (dy / dist) * speed,
                hx,
                hy,
                line,
                CYAN,
                0.0,
            )
        )
        self.think_busy = True
        if len(self.thoughts) > 6:
            self.thoughts = self.thoughts[-6:]

    def think(self, words: list[str], color: tuple[int, int, int]) -> None:
        _ = color
        self.thinking = " ".join(words)
        self.think_q.extend(self.wrap_think(self.thinking))
        self.thoughts = []
        self.think_board = []
        self.think_busy = False
        self.think_lift = 0.0
        self.think_hold = 2.8

    def plant(self, x: float, y: float, label: str) -> None:
        self.bases.append(Base(x, y, label))

    def set_file(self, path: str, lang: str, sky: tuple[int, int, int], tool: str = "") -> None:
        self.file = path
        self.lang = lang
        self.sky = sky
        self.sky_a = 1.0
        if tool:
            self.tool = tool

    def enter(self, i: int = 0, climb: bool = False) -> None:
        _ = i
        self.set_file("demo/score.py", "PYTHON", SKY_PY, "READ")
        self.code = list(SCORE_BUG)
        self.applied = set()
        self.caret = min(1, max(0, len(self.code) - 2))
        self.caption = "READ  ·  demo/score.py"
        self.shots = []
        self.thoughts = []
        self.think_q = []
        self.think_board = []
        self.think_busy = False
        self.think_lift = 0.0
        self.think_hold = 0.0
        self.think_a = 0.0
        self.thinking = ""
        self.talks = []
        self.talk_i = 0
        self.talk_until = 0.0
        self.state = "wander"
        self.flight = None
        self.done = set()
        _ = climb

    def clear_pad(self) -> None:
        self.code = [""]
        self.applied = set()
        self.caret = 0
        self.caption = f"CLEAR  ·  {self.lang}  ·  then think"

    def start_read(self) -> None:
        self.state = "wander"
        self.read_path = []
        self.flight = None
        self.tool = "READ"
        words: list[str] = []
        aims: list[int] = []
        cols: list[int] = []
        kinds: list[str] = []
        for i, line in enumerate(self.code):
            col = 0
            for part in line.split(" "):
                if not part:
                    col += 1
                    continue
                words.append(part)
                aims.append(i)
                cols.append(col)
                kinds.append("scan")
                col += len(part) + 1
        self.caption = "READ  ·  demo/score.py"
        if words:
            self.fire(words, aims, kinds, cols, CYAN)
        self.pulse = 0.45

    def say(self, text: str) -> None:
        pages = [text]
        if len(text) > 52:
            cut = text.rfind(" ", 0, 52)
            if cut < 12:
                cut = 52
            pages = [p for p in (text[:cut].strip(), text[cut:].strip()) if p]
        self.talks = pages
        self.talk_i = 0
        self.talk_until = self.t + 1.6 + min(2.4, 0.04 * len(pages[0]))
        self.caption = "SAY  ·  coder"

    def fire_lines(self, rows: list[str], color: tuple[int, int, int], kind: str = "add") -> None:
        self.code = [""] * max(len(rows), 1)
        self.applied = set()
        self.caret = 0
        self.fire(list(rows), list(range(len(rows))), [kind] * len(rows), [0] * len(rows), color)

    def shoot_bash(self, rows: list[str], ok: bool) -> None:
        self.set_file(rows[0][:48] if rows else "shell", "SH", SKY_GO, "BASH")
        self.caption = "BASH  ·  demo/test_score.py"
        self.fire_lines(rows, GRASS if ok else BRICK)

    def shoot_edit(self) -> None:
        self.set_file("demo/score.py", "PYTHON", SKY_PY, "EDIT")
        self.code = align_pad(SCORE_BUG, SCORE_FIX)
        lines, aims, kinds, cols = payload_plan(SCORE_BUG, SCORE_FIX)
        self.caption = "EDIT  ·  minus to plus"
        self.fire(lines, aims, kinds, cols, COIN)
        self.pulse = 1

    def shoot_write(self) -> None:
        self.set_file("demo/greet.py", "PYTHON", SKY_PY, "WRITE")
        self.caption = "WRITE  ·  demo/greet.py"
        self.fire_lines(GREET, GRASS)
        self.pulse = 1

    def apply_line(self, text: str, line_i: int | None = None, col: int = 0) -> None:
        """A word-bolt sticks at that line and column."""
        key = f"{line_i}:{col}:{text}"
        if key in self.applied:
            return
        self.applied.add(key)
        at = line_i if line_i is not None else len(self.code)
        while len(self.code) <= at:
            self.code.append("")
        row = self.code[at]
        if col > len(row):
            row = row + " " * (col - len(row))
        end = col + len(text)
        self.code[at] = row[:col] + text + row[end:]
        self.caret = at

    def update(self, dt: float) -> None:
        self.t += dt
        self.blink += dt
        self.pulse *= math.exp(-7 * dt)
        self.sky_a = max(0.0, self.sky_a - dt / 1.6)
        if self.flight:
            x0, y0, x1, y1, u, secs = self.flight
            u = min(1.0, u + dt / secs)
            k = exp_in_out(u)
            nx = x0 + (x1 - x0) * k
            ny = y0 + (y1 - y0) * k
            dx = nx - self.x
            self.x, self.y = nx, ny
            if abs(dx) > 8:
                self.facing = -1 if dx < 0 else 1
            self.flight = None if u >= 1 else (x0, y0, x1, y1, u, secs)
            if self.flight is None and self.state == "climb":
                self.state = "wander"
                self.phase = 0.4
        elif self.state == "wander":
            self.phase += dt
            bx, by, bw, bh = self.box
            cx, cy = bx + bw / 2, by + bh / 2
            tx = cx + (bw / 2 - 160) * math.sin(self.phase / 5.5 * math.pi * 2)
            ty = cy + (bh / 2 - 140) * math.sin(self.phase / 3.8 * math.pi * 2 + 1.1)
            ox, oy = self.x, self.y
            self.x += (tx - self.x) * (1 - math.exp(-5.5 * dt))
            self.y += (ty - self.y) * (1 - math.exp(-5.5 * dt))
            vx = (self.x - ox) / dt if dt > 0 else 0.0
            if vx < -28:
                self.facing = -1
            elif vx > 28:
                self.facing = 1
        self.angle = math.sin(self.t * 4.5 * math.pi * 2) * 0.08 if self.state == "typing" else self.angle * 0.88
        self.trail.append((self.x, self.y))
        if len(self.trail) > 22:
            self.trail = self.trail[-22:]
        live: list[Shot] = []
        for s in self.shots:
            s.age += dt
            dx, dy = s.hx - s.x, s.hy - s.y
            dist = math.hypot(dx, dy)
            step = math.hypot(s.vx, s.vy) * dt
            landed = s.form >= 1.0 or dist < max(12.0, step + 0.5)
            if not landed:
                k = 1 - math.exp(-7 * dt)
                speed = 360
                inv = 1 / (dist or 1)
                s.vx += (dx * inv * speed - s.vx) * k
                s.vy += (dy * inv * speed - s.vy) * k
                s.x += s.vx * dt
                s.y += s.vy * dt
                if (s.hx - s.x) * dx + (s.hy - s.y) * dy < 0:
                    landed = True
            if landed:
                s.x, s.y = s.hx, s.hy
                s.vx = s.vy = 0.0
                first = s.form < 1.0
                s.form = 1.0
                if first:
                    if s.kind == "add":
                        self.apply_line(s.text, s.idx, s.col)
                    elif s.kind == "cut" and s.idx < len(self.code):
                        row = self.code[s.idx]
                        col = s.col
                        if row[col : col + len(s.text)] == s.text:
                            self.code[s.idx] = row[:col] + " " * len(s.text) + row[col + len(s.text) :]
                    self.pulse = max(self.pulse, 0.55)
            if s.form >= 1.0:
                if s.age < s.life + 1.8:
                    live.append(s)
            elif s.age < s.life:
                live.append(s)
        self.shots = live
        self.fire_next_thought()
        self.think_lift += (0.0 - self.think_lift) * (1 - math.exp(-9 * dt))
        live_t: list[Thought] = []
        for th in self.thoughts:
            th.age += dt
            dx, dy = th.hx - th.x, th.hy - th.y
            dist = math.hypot(dx, dy)
            if dist < 14:
                th.form = 1.0
                th.x, th.y = th.hx, th.hy
                th.vx = th.vy = 0.0
                self.think_board.append(th.text)
                if len(self.think_board) > 8:
                    self.think_board = self.think_board[-8:]
                self.think_lift = 18.0
                self.think_busy = False
            else:
                k = 1 - math.exp(-9 * dt)
                speed = 420
                inv = 1 / (dist or 1)
                th.vx += (dx * inv * speed - th.vx) * k
                th.vy += (dy * inv * speed - th.vy) * k
                th.x += th.vx * dt
                th.y += th.vy * dt
                th.form = min(1.0, 1 - dist / 160)
                if th.age < th.life:
                    live_t.append(th)
        self.thoughts = live_t
        self.think_busy = any(th.form < 1.0 for th in self.thoughts)
        busy = bool(self.think_q or self.thoughts or self.think_busy)
        if busy:
            self.think_hold = 2.8
        else:
            self.think_hold = max(0.0, self.think_hold - dt)
        want = 1.0 if (busy or self.think_hold > 0) else 0.0
        self.think_a += (want - self.think_a) * (1 - math.exp(-7 * dt))
        if self.think_a < 0.02 and want == 0:
            self.think_a = 0.0
            self.thinking = ""
            self.think_board = []
        for b in self.bases:
            b.age += dt
        self.bases = [b for b in self.bases if b.age < b.life]
        if self.talks and self.t >= self.talk_until:
            if self.talk_i + 1 < len(self.talks):
                self.talk_i += 1
                page = self.talks[self.talk_i]
                self.talk_until = self.t + 1.4 + min(2.2, 0.04 * len(page))
            elif self.t >= self.talk_until + 0.8:
                pass

    def once(self, key: str) -> bool:
        if key in self.done:
            return False
        self.done.add(key)
        return True

    def script(self) -> None:
        t = self.t
        if t < 0.05 and self.once("enter"):
            self.enter()
            self.caption = "Busan Coder  ·  demo/"
            return
        if 0.50 <= t < 0.60 and self.once("read"):
            self.start_read()
        elif 2.10 <= t < 2.20 and self.once("think1"):
            self.think("read demo/score.py  n = n - s looks wrong".split(), CYAN)
            self.caption = "THINKING  ·  find the bug"
        elif 3.20 <= t < 3.30 and self.once("say1"):
            self.say("total subtracts. I will run the test.")
        elif 4.40 <= t < 4.50 and self.once("bash1"):
            self.shoot_bash(SHELL_FAIL, ok=False)
        elif 6.80 <= t < 6.90 and self.once("think2"):
            self.think("test failed  change minus to plus  then re-run".split(), CYAN)
            self.caption = "THINKING  ·  edit the sum"
        elif 8.00 <= t < 8.10 and self.once("edit"):
            self.shoot_edit()
        elif 10.60 <= t < 10.70 and self.once("think3"):
            self.think("run demo/test_score.py  expect ok".split(), CYAN)
        elif 11.70 <= t < 11.80 and self.once("bash2"):
            self.shoot_bash(SHELL_OK, ok=True)
        elif 13.80 <= t < 13.90 and self.once("say2"):
            self.say("Tests pass. I will write demo/greet.py next.")
        elif 15.10 <= t < 15.20 and self.once("think4"):
            self.think("write greet  hello causewaybay".split(), CYAN)
        elif 16.20 <= t < 16.30 and self.once("write"):
            self.shoot_write()
        elif 18.80 <= t < 18.90 and self.once("say3"):
            self.say("Read, bash, edit, bash, write. Job done.")
            self.caption = "DONE  ·  demo/"

    def tint(self, line: str, i: int) -> tuple[int, int, int]:
        if self.tool == "BASH" or self.lang == "SH":
            if line.startswith("$ "):
                return COIN
            if any(k in line for k in ("Error", "error", "Assertion", "==")):
                return BRICK
            return CREAM
        if self.tool == "READ" and i == 0:
            return CYAN
        if any(k in line for k in ("hello", "print", "ok", "return")):
            return GRASS
        if any(k in line for k in ("def ", "for ", "if ")):
            return PINK
        if i == 0:
            return CYAN
        return CREAM

    def draw_sea(self, buf: Buf) -> None:
        sky_high = (72, 148, 204)
        sky_dusk = (255, 168, 112)
        sea_lite = (48, 164, 188)
        sea_deep = (8, 48, 84)
        foam = (200, 236, 236)
        horizon = H * 38 // 100
        for i in range(18):
            k = i / 17
            col = mix(sky_high, sky_dusk, k * 0.72)
            if self.sky_a > 0.01:
                col = mix(col, self.sky, 0.10 * self.sky_a)
            buf.rect(0, horizon * i // 17, W, horizon // 17 + 1, col)
        buf.rect(0, horizon - 6, W, 10, mix(sky_dusk, sea_lite, 0.45), 0.85)
        water_h = H - horizon
        for i in range(24):
            k = i / 23
            buf.rect(0, horizon + water_h * i // 23, W, water_h // 23 + 1, mix(sea_lite, sea_deep, k))
        for i in range(8):
            y = horizon + 18 + i * 48
            phase = self.t * (0.7 + i * 0.05) + i * 1.4
            for x in range(0, W, 28):
                bob = math.sin(phase + x * 0.018) * 5
                buf.rect(x, y + bob, 20, 3, foam, 0.14 + 0.10 * ((i + x) % 2))
        for i in range(25):
            sx = (i * 211 + int(self.t * 18)) % W
            sy = horizon + 20 + (i * 47) % max(8, H - horizon - 40)
            buf.rect(sx, sy, 3, 2, foam, 0.22 + 0.18 * (0.5 + 0.5 * math.sin(self.t * 2.4 + i)))

    def draw(self, buf: Buf) -> None:
        self.draw_sea(buf)
        bx, by, bw, bh = self.box
        buf.rect(bx - 8, by - 8, bw + 16, bh + 16, mix(NAVY, self.sky, 0.18))
        buf.rect(bx, by, bw, 40, mix(INK, self.sky, 0.28))
        buf.rect(bx, by + 40, bw, bh - 40, WELL)
        buf.rect(bx, by + 40, 64, bh - 40, GUTTER)
        buf.text(self.file, bx + 16, by + 10, CREAM, 2)
        tag = self.tool or self.lang
        buf.text(tag, bx + bw - buf.text_w(tag, 2) - 16, by + 10, self.sky, 2)

        if self.think_a > 0.02:
            a = self.think_a
            wx, wy, ww, wh = self.think_well()
            buf.rect(int(wx) - 2, int(wy) - 2, int(ww) + 4, int(wh) + 4, INK, 0.96 * a)
            buf.rect(int(wx), int(wy), int(ww), int(wh), mix(NAVY, CYAN, 0.14), 0.96 * a)
            buf.rect(int(wx), int(wy), int(ww), 3, CYAN, a)
            buf.text("THINKING", int(wx) + 10, int(wy) + 8, CYAN, 2)
            vis = self.think_board[-3:]
            lh = 18
            for i, line in enumerate(vis):
                yy = int(wy + wh - 6 - (len(vis) - i) * lh + self.think_lift)
                if yy < wy + 24 or yy > wy + wh - 14:
                    continue
                buf.text(line, int(wx) + 10, yy, CREAM, 2)

        shown = self.code if self.code else [""]
        rows = max(8, len(shown) + 1)
        for i in range(rows):
            yy = by + 56 + i * 36
            if yy > by + bh - 28:
                break
            buf.text(f"{i + 1:>2}", bx + 14, yy, DIM, 2)
            line = shown[i] if i < len(shown) else ""
            # The bolt already wrote this row. Keep drawing it after the bug dies.
            if line:
                buf.text(line, bx + 80, yy, self.tint(line, i), 2)
            if i == self.caret and (self.blink % 0.9) < 0.55:
                caret_x = bx + 80 + (buf.text_w(line, 2) if line else 0)
                buf.rect(int(caret_x), yy - 2, 3, 22, COIN, 0.95)

        buf.rect(0, 0, W, 48, INK, 0.72)
        buf.text("Busan Coder", 20, 16, COIN, 2)
        credit = "Inspired by Causewaybay Hacker"
        buf.text(credit, W - buf.text_w(credit, 2) - 20, 16, CREAM, 2)

        for i, (tx, ty) in enumerate(self.trail):
            k = (i + 1) / max(1, len(self.trail))
            buf.diamond(tx, ty, 3 + 4 * k, CYAN, 0.12 * k)

        for b in self.bases:
            k = 1 - b.age / b.life
            r = 14 + 10 * (1 - math.exp(-4 * b.age))
            buf.glow(b.x, b.y, r * 2.2, COIN, 0.28 * k)
            buf.circle(b.x, b.y, r, COIN, 0.95 * k)
            buf.circle(b.x, b.y, r * 0.55, CYAN, 0.95 * k)
            tw = buf.text_w(b.label, 2)
            buf.rect(int(b.x - tw / 2 - 6), int(b.y + r + 6), tw + 12, 22, INK, 0.78 * k)
            buf.text(b.label, int(b.x - tw / 2), int(b.y + r + 9), CREAM, 2, k)

        for s in self.shots:
            ink = BRICK if getattr(s, "kind", "add") == "cut" else s.color
            stuck = s.form >= 1.0
            if stuck:
                continue
            buf.diamond(s.x, s.y, 8, ink, 0.95)
            tw = buf.text_w(s.text, 2)
            # Nose leads; glyphs trail so a long println does not fly past the row.
            tx = int(s.x) if s.vx < 0 else int(s.x - tw)
            ty = int(s.y)
            buf.text(s.text, tx + 1, ty + 1, INK, 2)
            buf.text(s.text, tx, ty, ink, 2)

        for th in self.thoughts:
            if th.form >= 1.0:
                continue
            buf.diamond(th.x - 6, th.y + 8, 8, CYAN, 0.95)
            buf.text(th.text, int(th.x) + 1, int(th.y) + 1, INK, 2)
            buf.text(th.text, int(th.x), int(th.y), CYAN, 2)

        thrust = 1.15 if self.state == "climb" else 0.7
        for i in range(8):
            fy = self.y + 28 + i * 5 * thrust
            buf.diamond(self.x, fy, 6 - i * 0.45, mix(CYAN, COIN, i / 8), 0.55 * thrust)
        bob = math.sin(self.t * 1.6 * math.pi * 2) * 4.0
        draw_ship(buf, self.x, self.y + bob, self.facing, self.scale, self.angle, self.pulse, self.sky)

        if getattr(self, "scanlines", True):
            for y in range(0, H, 3):
                buf.rect(0, y, W, 1, INK, 0.10)

        if any(str(t or "").strip() for t in self.talks):
            tx, ty, tw, th = self.talk_well()
            page = self.talks[self.talk_i] if self.talks else ""
            buf.rect(int(tx) - 2, int(ty) - 2, int(tw) + 4, int(th) + 4, INK, 0.92)
            buf.rect(int(tx), int(ty), int(tw), int(th), CREAM, 0.96)
            buf.rect(int(tx), int(ty), int(tw), 4, COIN, 1)
            buf.text("BUSAN", int(tx) + 10, int(ty) + 8, INK, 2)
            width = max(8, int((tw - 24) / 16))
            rest = " ".join((page or "").split())
            lines: list[str] = []
            while rest and len(lines) < 3:
                if len(rest) <= width:
                    lines.append(rest)
                    break
                cut = rest.rfind(" ", 0, width)
                if cut < 8:
                    cut = width
                lines.append(rest[:cut].strip())
                rest = rest[cut:].strip()
            for i, line in enumerate(lines):
                buf.text(line, int(tx) + 10, int(ty) + 32 + i * 18, INK, 2)


def step_logic(demo: Demo, dt: float = DT) -> None:
    demo.script()
    demo.update(dt)


def step(demo: Demo, buf: Buf) -> None:
    step_logic(demo)
    demo.draw(buf)


def play_web() -> int:
    from raid_agent import serve

    return serve()


def _chrome() -> str | None:
    for name in ("chromium", "chromium-browser", "google-chrome", "chrome"):
        path = shutil.which(name)
        if path:
            return path
    return None


def record_web(out: Path, secs: float) -> int:
    import queue
    import threading

    from raid_agent import RECORD_DONE, make_httpd, set_record_queue

    chrome = _chrome()
    if chrome is None:
        print("need chromium on PATH to record the web demo", file=sys.stderr)
        return 1
    if shutil.which("ffmpeg") is None:
        print("need ffmpeg on PATH", file=sys.stderr)
        return 1

    frames: queue.Queue[bytes] = queue.Queue(maxsize=90)
    set_record_queue(frames)
    httpd, port = make_httpd("127.0.0.1", 8765)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{port}/?record=1"
    print(url, file=sys.stderr)

    cmd = [
        chrome,
        "--headless=new",
        "--disable-gpu",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-extensions",
        "--user-data-dir=/tmp/raid-chrome-record",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        f"--window-size={W},{H}",
        url,
    ]
    browser = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ff = subprocess.Popen(
        [
            "ffmpeg",
            "-y",
            "-f",
            "image2pipe",
            "-framerate",
            str(FPS),
            "-i",
            "-",
            "-c:v",
            "libx264",
            "-preset",
            "slow",
            "-tune",
            "animation",
            "-crf",
            "16",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(out),
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    assert ff.stdin is not None
    got = 0
    n = max(1, int(secs * FPS))
    deadline = time.time() + max(90.0, secs + 60.0)
    idle = 0
    try:
        while time.time() < deadline:
            try:
                frame = frames.get(timeout=2)
                idle = 0
            except queue.Empty:
                idle += 1
                if RECORD_DONE.is_set() and frames.empty():
                    break
                if browser.poll() is not None and frames.empty():
                    print("chromium exited early", file=sys.stderr)
                    break
                if idle >= 8 and got > 30:
                    break
                continue
            ff.stdin.write(frame)
            got += 1
            if got % 30 == 0:
                print(f"  frame {got}", file=sys.stderr)
            if RECORD_DONE.is_set() and frames.empty() and got >= 30:
                break
            if got >= n and RECORD_DONE.is_set():
                break
    finally:
        try:
            ff.stdin.close()
        except BrokenPipeError:
            pass
        browser.terminate()
        try:
            browser.wait(timeout=5)
        except subprocess.TimeoutExpired:
            browser.kill()
        httpd.shutdown()
        set_record_queue(None)
    err = ff.stderr.read().decode("utf-8", "replace") if ff.stderr else ""
    rc = ff.wait()
    if rc != 0:
        print(err[-2000:], file=sys.stderr)
        print("ffmpeg failed", file=sys.stderr)
        return rc
    print(out.resolve())
    return 0


def play_window(secs: float, loop: bool = True) -> int:
    import gi

    gi.require_version("Gtk", "3.0")
    gi.require_version("Gdk", "3.0")
    from gi.repository import Gdk, GdkPixbuf, GLib, Gtk

    demo = Demo()
    demo.scanlines = False
    buf = Buf(W, H)
    n = max(1, int(secs * FPS))
    frame_i = 0
    hold: dict[str, object] = {"pb": None, "data": None}
    acc = 0.0
    last = time.perf_counter()

    def make_pixbuf() -> GdkPixbuf.Pixbuf:
        data = bytes(buf.pix)
        hold["data"] = data
        pb = GdkPixbuf.Pixbuf.new_from_bytes(
            GLib.Bytes.new(data),
            GdkPixbuf.Colorspace.RGB,
            False,
            8,
            W,
            H,
            W * 3,
        )
        hold["pb"] = pb
        return pb

    step(demo, buf)
    frame_i = 1
    make_pixbuf()

    win = Gtk.Window(title="Busan Coder")
    win.set_default_size(W, H)
    da = Gtk.DrawingArea()
    da.set_size_request(W, H)
    win.add(da)
    win.connect("destroy", Gtk.main_quit)

    def on_draw(_widget, cr) -> bool:
        pb = hold["pb"]
        if pb is None:
            return False
        alloc = da.get_allocation()
        if alloc.width < 1 or alloc.height < 1:
            return False
        s = min(alloc.width / W, alloc.height / H)
        cr.translate((alloc.width - W * s) * 0.5, (alloc.height - H * s) * 0.5)
        cr.scale(s, s)
        Gdk.cairo_set_source_pixbuf(cr, pb, 0, 0)
        cr.paint()
        return False

    def on_key(_w, event) -> bool:
        if event.keyval in (Gdk.KEY_Escape, Gdk.KEY_q, Gdk.KEY_Q):
            Gtk.main_quit()
            return True
        return False

    da.connect("draw", on_draw)
    win.connect("key-press-event", on_key)
    win.show_all()

    def tick() -> bool:
        nonlocal demo, frame_i, acc, last
        now = time.perf_counter()
        acc = min(0.25, acc + (now - last))
        last = now
        moved = False
        while acc >= DT:
            if frame_i >= n:
                if not loop:
                    demo.draw(buf)
                    make_pixbuf()
                    da.queue_draw()
                    return False
                demo = Demo()
                demo.scanlines = False
                frame_i = 0
            step_logic(demo)
            acc -= DT
            frame_i += 1
            moved = True
        if moved:
            demo.draw(buf)
            make_pixbuf()
            da.queue_draw()
        return True

    GLib.timeout_add(16, tick)
    Gtk.main()
    return 0


def encode_pipe(out: Path) -> subprocess.Popen:
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s",
        f"{W}x{H}",
        "-r",
        str(FPS),
        "-i",
        "-",
        "-c:v",
        "libx264",
        "-preset",
        "slow",
        "-tune",
        "animation",
        "-crf",
        "16",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(out),
    ]
    return subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=None, help="mp4 path; implies --record")
    ap.add_argument("--secs", type=float, default=90.0)
    ap.add_argument("--record", action="store_true", help="capture the live web UI to mp4")
    ap.add_argument("--gtk", action="store_true", help="open the old GTK window instead of the browser")
    ap.add_argument("--no-loop", action="store_true", help="in the GTK window, play once then freeze")
    args = ap.parse_args()
    if not args.record and args.out is None:
        if args.gtk:
            try:
                return play_window(args.secs, loop=not args.no_loop)
            except Exception as exc:
                print(f"live window failed ({exc}); try the web demo", file=sys.stderr)
                return 1
        return play_web()
    out = Path(args.out or "out/raid_demo.mp4")
    out.parent.mkdir(parents=True, exist_ok=True)
    return record_web(out, args.secs)


if __name__ == "__main__":
    raise SystemExit(main())
