"""Tool security classification for the Yeisme fork.

Upstream registers its MCP tools with no safety tier. The Gateway layer needs
a machine-readable mapping from every registered tool to one of four levels so
export profiles can include read/write tools while keeping generate (billed
external provider calls) and exec (arbitrary Blender code execution) opt-in.

The table in this module is the single source of truth:

- ``scripts/verify_tool_classification.py`` fails when the server registers a
  tool that is missing from the table (upstream added one) or when the table
  references a tool the server no longer registers.
- ``scripts/export_tool_classification.py`` regenerates the checked-in JSON
  artifact ``config/tool-classification.json`` from this module.

Levels:

- ``read``: observation only (scene info, search, status, polling). Safe to
  expose through the Gateway by default.
- ``write``: mutates the local Blender scene or local settings (downloads a
  licensed asset, sets a texture, imports a generated file, records
  feedback). Exposed by default but each call leaves an approval receipt.
- ``generate``: calls an external paid provider (Hyper3D Rodin, Hunyuan3D).
  Never in the default export profile; enabling requires explicit user
  approval plus user-owned credentials.
- ``exec``: arbitrary Python execution inside Blender. Never appears in any
  Gateway export profile; local direct connection only.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

LEVELS: tuple[str, ...] = ("read", "write", "generate", "exec")

#: Levels that must never appear in a generated Gateway export profile.
NON_EXPORTABLE_LEVELS: tuple[str, ...] = ("generate", "exec")

#: The Gateway caps total public tools per registry at this number.
GATEWAY_MAX_PUBLIC_TOOLS = 20

#: Write-level tools included in the default generated export profile.
#: Operators may add more write tools (subject to the public tool cap);
#: generate/exec tools can never be added by the generator.
DEFAULT_EXPORT_WRITE_TOOLS: tuple[str, ...] = (
    "download_polyhaven_asset",
    "set_texture",
)

TOOL_CLASSIFICATION: dict[str, str] = {
    "disable_telemetry": "write",
    "download_polyhaven_asset": "write",
    "download_polypizza_model": "write",
    "download_sketchfab_model": "write",
    "execute_blender_code": "exec",
    "generate_hunyuan3d_model": "generate",
    "generate_hyper3d_model_via_images": "generate",
    "generate_hyper3d_model_via_text": "generate",
    "get_addon_status": "read",
    "get_hunyuan3d_status": "read",
    "get_hyper3d_status": "read",
    "get_object_info": "read",
    "get_polyhaven_categories": "read",
    "get_polyhaven_status": "read",
    "get_polypizza_status": "read",
    "get_scene_info": "read",
    "get_sketchfab_model_preview": "read",
    "get_sketchfab_status": "read",
    "get_viewport_screenshot": "read",
    "import_generated_asset": "write",
    "import_generated_asset_hunyuan": "write",
    "poll_hunyuan_job_status": "read",
    "poll_rodin_job_status": "read",
    "record_trajectory_feedback": "write",
    "search_polyhaven_assets": "read",
    "search_polypizza_models": "read",
    "search_sketchfab_models": "read",
    "set_texture": "write",
}

#: Keys read by the Blender addon for external provider credentials. Used by
#: the degraded-state heuristic; values are never read, only presence checks.
PROVIDER_CREDENTIAL_ENV_VARS: dict[str, str] = {
    "hyper3d": "BLENDERMCP_HYPER3D_API_KEY",
    "sketchfab": "BLENDERMCP_SKETCHFAB_API_KEY",
    "polypizza": "BLENDERMCP_POLYPIZZA_API_KEY",
}

JSON_SCHEMA_NAME = "blender-mcp.tool-classification.v1"


def tools_for_level(level: str) -> list[str]:
    """Return the sorted tool names classified at ``level``."""
    return sorted(name for name, lvl in TOOL_CLASSIFICATION.items() if lvl == level)


def default_export_tools() -> list[str]:
    """Tools the generated Gateway export profile exposes by default.

    All read-level tools plus the curated write whitelist. Generate and exec
    tools are structurally excluded (see :func:`assert_exportable`).
    """
    tools = tools_for_level("read") + sorted(DEFAULT_EXPORT_WRITE_TOOLS)
    assert_exportable(tools)
    return sorted(tools)


def assert_exportable(tools: Iterable[str]) -> None:
    """Raise ``ValueError`` if ``tools`` contains a non-exportable entry.

    This is the hard guard behind the "exec never enters an export profile"
    and "generate never enters a default export profile" requirements: the
    registry example generator calls it before emitting YAML.
    """
    non_exportable = sorted(
        tool for tool in tools if TOOL_CLASSIFICATION.get(tool) in NON_EXPORTABLE_LEVELS
    )
    if non_exportable:
        raise ValueError(
            "non-exportable tools must not appear in a Gateway export profile: "
            + ", ".join(non_exportable)
        )
    unknown = sorted(tool for tool in tools if tool not in TOOL_CLASSIFICATION)
    if unknown:
        raise ValueError("tools missing from the classification table: " + ", ".join(unknown))


def classification_errors(
    registered_tools: Iterable[str],
    table: dict[str, str] | None = None,
) -> list[str]:
    """Compare ``registered_tools`` against the classification ``table``.

    Returns a list of human-readable problems (empty when consistent):

    - unclassified: registered but absent from the table (upstream added one)
    - unknown: in the table but not registered (tool removed or renamed)
    - bad level: table entry using a level outside :data:`LEVELS`
    """
    if table is None:
        table = TOOL_CLASSIFICATION
    problems: list[str] = []
    registered = set(registered_tools)
    unclassified = sorted(registered - set(table))
    if unclassified:
        problems.append(
            "unclassified tools (registered by the server but missing from the "
            "classification table): " + ", ".join(unclassified)
        )
    unknown = sorted(set(table) - registered)
    if unknown:
        problems.append(
            "unknown tools (in the classification table but not registered by "
            "the server): " + ", ".join(unknown)
        )
    bad_levels = sorted(
        f"{name}={level}"
        for name, level in table.items()
        if level not in LEVELS
    )
    if bad_levels:
        problems.append("invalid classification levels: " + ", ".join(bad_levels))
    return problems


async def registered_tool_names() -> list[str]:
    """Enumerate the tool names the MCP server actually registers.

    Imports :mod:`blender_mcp.server` lazily so importing this module stays
    side-effect free. Tool registration happens at import time; the lifespan
    (which would try to reach Blender) only runs when the server runs.
    """
    from blender_mcp.server import mcp

    tools = await mcp.list_tools()
    return sorted(tool.name for tool in tools)


def classification_to_json() -> dict:
    """Build the machine-readable classification payload."""
    return {
        "schema": JSON_SCHEMA_NAME,
        "levels": list(LEVELS),
        "nonExportableLevels": list(NON_EXPORTABLE_LEVELS),
        "gatewayMaxPublicTools": GATEWAY_MAX_PUBLIC_TOOLS,
        "defaultExportTools": default_export_tools(),
        "providerCredentialEnvVars": dict(PROVIDER_CREDENTIAL_ENV_VARS),
        "tools": {
            level: tools_for_level(level)
            for level in LEVELS
        },
        "counts": {
            "total": len(TOOL_CLASSIFICATION),
            **{level: len(tools_for_level(level)) for level in LEVELS},
        },
    }


def export_json(path: Path | str) -> Path:
    """Write the machine-readable classification artifact to ``path``."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(classification_to_json(), indent=2) + "\n"
    path.write_text(payload, encoding="utf-8")
    return path


def json_artifact_in_sync(path: Path | str) -> tuple[bool, str]:
    """Check that the checked-in JSON artifact matches this module.

    Returns ``(in_sync, detail)``. When out of sync the detail names the
    regeneration command.
    """
    path = Path(path)
    if not path.exists():
        return False, f"{path} is missing; run scripts/export_tool_classification.py"
    current = json.dumps(classification_to_json(), indent=2) + "\n"
    on_disk = path.read_text(encoding="utf-8")
    if on_disk != current:
        return False, f"{path} is stale; run scripts/export_tool_classification.py"
    return True, "classification JSON artifact is in sync"


def repo_default_json_path() -> Path:
    """Default checked-in artifact path, resolved relative to this file."""
    return Path(__file__).resolve().parents[2] / "config" / "tool-classification.json"


def load_json_artifact(path: Path | str | None = None) -> dict:
    """Load a classification JSON artifact (inverse of :func:`export_json`)."""
    path = Path(path) if path is not None else repo_default_json_path()
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != JSON_SCHEMA_NAME:
        raise ValueError(f"unsupported classification schema in {path}")
    return data


def json_artifact_matches_module(path: Path | str | None = None) -> list[str]:
    """Problems preventing the JSON artifact from being the module's mirror."""
    try:
        data = load_json_artifact(path)
    except FileNotFoundError:
        return ["classification JSON artifact is missing"]
    except ValueError as exc:
        return [str(exc)]
    problems: list[str] = []
    expected = classification_to_json()
    for key in ("levels", "nonExportableLevels", "defaultExportTools", "tools", "counts"):
        if data.get(key) != expected[key]:
            problems.append(f"JSON field {key!r} differs from the module table")
    return problems


def missing_provider_credentials(env: dict[str, str] | None = None) -> list[str]:
    """Provider source names whose credential env var is unset.

    ``env`` defaults to ``os.environ``; only key presence is checked, values
    are never inspected or reported.
    """
    import os

    env = os.environ if env is None else env
    return sorted(
        source
        for source, var in PROVIDER_CREDENTIAL_ENV_VARS.items()
        if not env.get(var)
    )
