#!/usr/bin/env python
"""Verify the tool classification table against the live MCP server.

Run from the repository root:

    uv run python scripts/verify_tool_classification.py

Exit codes:

- ``0``: the table covers exactly the tools the server registers, levels are
  valid, and the checked-in JSON artifact is in sync.
- ``1``: drift detected (unclassified tools, stale entries, or a stale JSON
  artifact). The output names the offending tools and the fix command.

This is the gate behind "上游新增工具未分级时 fail": after an upstream sync
that introduces a new ``@mcp.tool``, this script fails until the new tool is
classified in ``src/blender_mcp/tool_classification.py`` and the JSON artifact
is regenerated.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from blender_mcp import tool_classification as tc


async def collect_problems() -> list[str]:
    problems: list[str] = []
    try:
        registered = await tc.registered_tool_names()
    except Exception as exc:  # pragma: no cover - environment failure
        return [f"could not enumerate registered tools: {exc}"]

    problems.extend(tc.classification_errors(registered))

    if len(registered) != len(set(registered)):  # pragma: no cover - paranoia
        problems.append("server reported duplicate tool names")

    in_sync, detail = tc.json_artifact_in_sync(tc.repo_default_json_path())
    if not in_sync:
        problems.append(detail)
    return problems


def main() -> int:
    problems = asyncio.run(collect_problems())
    if problems:
        print("tool classification verification FAILED:")
        for problem in problems:
            print(f"  - {problem}")
        print(
            "fix: update TOOL_CLASSIFICATION in "
            "src/blender_mcp/tool_classification.py, then run "
            "`uv run python scripts/export_tool_classification.py`"
        )
        return 1
    table = tc.TOOL_CLASSIFICATION
    print(f"tool classification OK: {len(table)} tools classified")
    for level in tc.LEVELS:
        print(f"  {level:<8} {len(tc.tools_for_level(level))}")
    print(f"  default export profile: {len(tc.default_export_tools())} tools "
          f"(cap {tc.GATEWAY_MAX_PUBLIC_TOOLS})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
