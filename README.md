# Busan Coder

Grok coding agent with a chalkboard pad and a ship. Inspired by Causewaybay Hacker.

Auth is the same file Fun uses: `~/.local/share/fun/auth.json`.

## Run

```bash
python3 -m fighter --name "Busan Coder"
python3 love2d/run.py
```

`python3 -m fighter` is the Grok loop + tools + HTTP pad API.
`love2d/run.py` is the LÖVE pad talking to that API.

Enter sends to Grok. Thinking streams into the box. Tools: read, write, edit, bash.

If you are not logged in, type `login` / Ctrl+L. Custom agent example: `python3 examples/sky_raider.py`.

Record a live coding turn (`docs/demo.mp4`, workspace `/tmp/demo`):

```bash
PYTHONPATH=$HOME/demo python3 scripts/record-demo.py
```

## Build your own fighter

```python
from fighter import Agent, serve, tool

@tool("ping", "Return pong.", {"type": "object", "properties": {}, "required": []})
def ping(_args):
    return "pong"

agent = Agent(
    "Sky Raider",
    callsign="RAIDER",
    workspace=".",
    extra_instructions="Keep replies short. Fix, then verify.",
    extra_tools=[ping],
)
serve(agent)
```

LÖVE pad:

```lua
local pad = require("pad")
local demo = pad.Demo.new()
pad.client.apply(demo, event, { name = "Busan Coder", callsign = "BUSAN" })
```

`pad/` is theme, chalkboard, ship, and the Grok event mapper.
`fighter/` is identity, tools, Grok, and `serve(agent)`.

Env: `BUSAN_AGENT`, `BUSAN_HOST`, `BUSAN_PORT`, `BUSAN_DEMO`.

## Needs

- Python 3.10+
- LÖVE 11 (or a browser)
- Fun Grok login (`fun login` or the login button)
- `ffmpeg` with `libx264` only if recording
