"""Busan Coder — Grok + tools + pad UI.

    from fighter import Agent, serve, tool

    agent = Agent("Busan Coder", extra_instructions="Keep replies short.")
    serve(agent)

Shell:

    python3 -m fighter --name "Busan Coder"

LÖVE pad (same HTTP API):

    python3 love2d/run.py
"""
from fighter.agent import Agent, AgentConfig
from fighter.server import RECORD_DONE, make_httpd, serve, set_record_queue
from fighter.tools import Tool, builtin_tools, tool

__all__ = [
    "Agent",
    "AgentConfig",
    "RECORD_DONE",
    "Tool",
    "builtin_tools",
    "make_httpd",
    "serve",
    "set_record_queue",
    "tool",
]
