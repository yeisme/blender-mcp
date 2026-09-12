#!/usr/bin/env python
"""Blender first-run journey CLI (task 1.4).

    uv run python scripts/blender_first_run.py snippet        # paste-in registry fragment
    uv run python scripts/blender_first_run.py state          # probe + print connection state
    uv run python scripts/blender_first_run.py state --json   # machine-readable probe result
    uv run python scripts/blender_first_run.py state --probe-roundtrip  # full read-tool roundtrip

``state`` probes, in order: the user registry (default location, override
with ``--registry``), whether the stdio server can be launched, whether the
loopback addon socket answers, and -- with ``--probe-roundtrip`` -- whether a
read tool returns a real payload over MCP stdio. Every probe stays on the
local machine; no external service is contacted and no credential value is
read.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import socket
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from blender_mcp import first_run as fr
from blender_mcp import gateway_registry as gr
from blender_mcp import tool_classification as tc

DEFAULT_HOST = "localhost"
DEFAULT_PORT = 9876
DEFAULT_REGISTRY = Path.home() / ".mcp-gateway" / "registry.yaml"


def probe_registry(path: Path) -> bool | None:
    """True/False when the file is readable; None when it does not exist."""
    if not path.exists():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    if fr.registry_disabled_blender(text):
        return False
    return fr.registry_mentions_blender(text)


def probe_server_runnable(timeout: float = 30.0) -> bool | None:
    """Launch the server entry point locally and check it exits cleanly.

    Uses ``uv run blender-mcp --help`` from the repository, which imports the
    server package and exercises the console script without contacting any
    external service (``--help`` is handled by the addon installer CLI and
    exits immediately).
    """
    repo_root = Path(__file__).resolve().parents[1]
    try:
        proc = subprocess.run(
            ["uv", "run", "blender-mcp", "--help"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return proc.returncode == 0


def probe_socket(host: str | None = None, port: int | None = None, timeout: float = 1.5) -> bool | None:
    """Try the loopback addon socket. Never connects off-loopback by default."""
    host = host or os.getenv("BLENDER_HOST", DEFAULT_HOST)
    port = port if port is not None else int(os.getenv("BLENDER_PORT", DEFAULT_PORT))
    if host not in ("localhost", "127.0.0.1", "::1"):
        # The addon only ever listens on loopback; refuse to probe elsewhere.
        return None
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


async def probe_read_roundtrip(timeout: float = 45.0) -> bool | None:
    """Spawn the MCP server over stdio and call a read tool.

    Success means the tool returned a JSON payload (``get_addon_status``
    returns ``{"up_to_date": ...}`` on success and an ``Error ...`` string
    when the addon is down).
    """
    repo_root = Path(__file__).resolve().parents[1]

    async def run() -> bool | None:
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
        except ImportError:
            return None
        params = StdioServerParameters(
            command="uv",
            args=["run", "blender-mcp"],
            cwd=str(repo_root),
        )

        async def roundtrip() -> bool:
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool("get_addon_status", {})
                    return "".join(
                        part.text for part in result.content if hasattr(part, "text")
                    )

        try:
            text = await asyncio.wait_for(roundtrip(), timeout=timeout)
            payload = json.loads(text)
            return isinstance(payload, dict) and "up_to_date" in payload
        except Exception:
            return False

    return await run()


def build_facts(args: argparse.Namespace) -> fr.StateInput:
    registry_ok = probe_registry(Path(args.registry).expanduser())
    facts = fr.StateInput(registry_has_blender=registry_ok)
    facts.server_runnable = probe_server_runnable()
    facts.socket_reachable = probe_socket()
    if args.probe_roundtrip and facts.socket_reachable:
        facts.read_roundtrip_ok = asyncio.run(probe_read_roundtrip())
    facts.missing_credentials = tc.missing_provider_credentials()
    return facts


def cmd_snippet(args: argparse.Namespace) -> int:
    sys.stdout.write(gr.build_fragment())
    return 0


def cmd_state(args: argparse.Namespace) -> int:
    facts = build_facts(args)
    state = fr.determine_state(facts)
    copy = fr.state_copy(state)
    if args.json:
        sys.stdout.write(
            json.dumps(
                {
                    "state": state.value,
                    "title": copy["title"],
                    "message": copy["message"],
                    "action": copy["action"],
                    "probes": {
                        "registry_has_blender": facts.registry_has_blender,
                        "server_runnable": facts.server_runnable,
                        "socket_reachable": facts.socket_reachable,
                        "read_roundtrip_ok": facts.read_roundtrip_ok,
                        "missing_credentials": facts.missing_credentials,
                    },
                },
                indent=2,
            )
            + "\n"
        )
    else:
        print(fr.render_state_line(state))
        print("诊断路径: mcp-gateway diagnose blender → mcp-gateway doctor → mcp-gateway tools")
    return 0 if state is fr.ConnectionState.READY else 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("snippet", help="print the paste-in servers: fragment")

    state = sub.add_parser("state", help="probe and print the connection state")
    state.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    state.add_argument(
        "--probe-roundtrip",
        action="store_true",
        help="also spawn the server over stdio and call a read tool",
    )
    state.add_argument("--json", action="store_true", help="machine-readable output")

    args = parser.parse_args(argv)
    if args.command == "snippet":
        return cmd_snippet(args)
    return cmd_state(args)


if __name__ == "__main__":
    raise SystemExit(main())
