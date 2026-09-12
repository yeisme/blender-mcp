#!/usr/bin/env python
"""Generate the sanitized Gateway registry example (task 1.2).

    uv run python scripts/generate_gateway_registry_example.py            # regenerate
    uv run python scripts/generate_gateway_registry_example.py --check    # drift guard
    uv run python scripts/generate_gateway_registry_example.py --fragment # print paste-in block
    uv run python scripts/generate_gateway_registry_example.py --validate # + mcp-gateway config validate

The example exposes namespace ``blender`` with read + curated write tools.
generate and exec tools can never be emitted: the builder raises first. The
full example uses loopback placeholder gateway values and passes
``mcp-gateway config validate --registry`` when the CLI is installed.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from blender_mcp import gateway_registry as gr
from blender_mcp import tool_classification as tc

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / "docs" / "gateway" / "registry-blender-example.yaml"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="example path")
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the checked-in example matches regeneration (no write)",
    )
    parser.add_argument(
        "--fragment",
        action="store_true",
        help="print the paste-in servers: fragment instead of writing files",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="also run mcp-gateway config validate on the example (skips if CLI missing)",
    )
    args = parser.parse_args()

    if args.fragment:
        sys.stdout.write(gr.build_fragment())
        return 0

    expected = gr.build_full_example()
    path = Path(args.output)

    if args.check:
        if not path.exists():
            print(f"FAIL: {path} is missing; run the generator without --check")
            return 1
        if path.read_text(encoding="utf-8") != expected:
            print(f"FAIL: {path} is stale; rerun the generator")
            return 1
        print(f"OK: {path} matches regeneration")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(expected, encoding="utf-8")
        print(f"wrote {path}")

    tools = gr.export_tools()
    print(f"namespace {gr.NAMESPACE}: {len(tools)} tools exposed "
          f"(read {len(tc.tools_for_level('read'))} + curated write "
          f"{len(tc.DEFAULT_EXPORT_WRITE_TOOLS)}, cap {tc.GATEWAY_MAX_PUBLIC_TOOLS})")
    print("excluded by design: " + ", ".join(
        sorted(tc.tools_for_level("generate") + tc.tools_for_level("exec"))
    ))

    if args.validate:
        try:
            ok, output = gr.validate_with_gateway_cli(str(path))
        except FileNotFoundError as exc:
            print(f"SKIP: {exc}")
            return 0
        print(output)
        if not ok:
            print("FAIL: gateway validation rejected the example")
            return 1
        print("OK: mcp-gateway config validate accepted the example")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
