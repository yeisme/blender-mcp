#!/usr/bin/env python
"""Regenerate the machine-readable tool classification artifact.

    uv run python scripts/export_tool_classification.py [--output PATH]

Writes ``config/tool-classification.json`` from the module table. Per repo
policy the structured metadata artifact is script-generated, never hand
edited. The verify script fails CI when the artifact drifts from the module.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from blender_mcp import tool_classification as tc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default=str(tc.repo_default_json_path()),
        help="artifact path (default: config/tool-classification.json)",
    )
    args = parser.parse_args()

    path = tc.export_json(args.output)
    print(f"wrote {path} ({len(tc.TOOL_CLASSIFICATION)} tools)")
    in_sync, detail = tc.json_artifact_in_sync(tc.repo_default_json_path())
    if not in_sync:  # pragma: no cover - only when --output points elsewhere
        print(detail)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
