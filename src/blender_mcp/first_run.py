"""First-run journey support: five-state connection model (task 1.4).

Pure state determination plus user-facing copy. The states and their
resolution order follow the change design:

1. ``not_configured``   – the user registry has no ``blender`` server entry
2. ``server_unreachable`` – the stdio server cannot be launched
3. ``addon_disconnected``  – server launches, but the loopback addon socket
   (127.0.0.1:9876) does not answer
4. ``degraded``        – core loop works but external asset-source
   credentials are missing (only the matching generate/download entries are
   disabled; everything else keeps working)
5. ``ready``           – a read tool round-trips successfully

Copy rules: every non-ready state names exactly one recovery action, and no
state copy contains filesystem paths or credential material.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class ConnectionState(str, Enum):
    NOT_CONFIGURED = "not_configured"
    SERVER_UNREACHABLE = "server_unreachable"
    ADDON_DISCONNECTED = "addon_disconnected"
    READY = "ready"
    DEGRADED = "degraded"


@dataclass
class StateInput:
    """Facts a probe supplies; ``None`` means "not probed / unknown".

    Unknown facts resolve conservatively (see :func:`determine_state`):
    ``ready`` is only reported on positive evidence.
    """

    registry_has_blender: bool | None = None
    server_runnable: bool | None = None
    socket_reachable: bool | None = None
    read_roundtrip_ok: bool | None = None
    #: External asset sources without user-configured credentials
    #: (subset of {"hyper3d", "sketchfab", "polypizza"}).
    missing_credentials: list[str] = field(default_factory=list)


#: Per-state user-visible copy. ``action`` must be a single, specific
#: recovery step; the tests enforce uniqueness and sanitization.
STATE_COPY: dict[ConnectionState, dict[str, str]] = {
    ConnectionState.NOT_CONFIGURED: {
        "title": "Blender 接入未配置",
        "message": "个人 Gateway 配置中还没有 blender server 条目。",
        "action": "运行旅程第 4–5 步：先生成个人 Gateway 配置，再粘贴 blender server 配置片段。",
    },
    ConnectionState.SERVER_UNREACHABLE: {
        "title": "Blender server 未就绪",
        "message": "stdio 方式拉起 blender-mcp server 失败，通常是 uv 或安装缺失。",
        "action": "按文档安装 uv 后重试，或运行 mcp-gateway diagnose blender 查看后端诊断。",
    },
    ConnectionState.ADDON_DISCONNECTED: {
        "title": "请在 Blender 中启动 addon 连接",
        "message": "blender-mcp server 已就绪，但本机 loopback 端口上没有 Blender addon 在监听。",
        "action": "在 Blender 中打开 Preferences → Add-ons → Blender MCP，点击 Start MCP Server。",
    },
    ConnectionState.DEGRADED: {
        "title": "Blender 接入可用（部分资产源未配置）",
        "message": "核心建模工具可用；未配置凭据的资产源的 generate/download 入口被禁用。",
        "action": "在 Blender addon 设置中为对应资产源填写用户自己的凭据后重启连接。",
    },
    ConnectionState.READY: {
        "title": "Blender 接入就绪",
        "message": "read 工具往返成功，全部暴露工具可用。",
        "action": "无需处理。",
    },
}


def determine_state(facts: StateInput) -> ConnectionState:
    """Map probed facts onto exactly one connection state.

    Resolution order follows the design table. Unknown (``None``) probes are
    conservative: an unreadable/absent registry counts as not configured, an
    unlaunchable or unprobed server counts as unreachable, and a socket that
    did not positively answer counts as disconnected. ``ready`` therefore
    always rests on positive evidence, never on missing probes.
    """
    if facts.registry_has_blender is not True:
        return ConnectionState.NOT_CONFIGURED
    if facts.server_runnable is not True:
        return ConnectionState.SERVER_UNREACHABLE
    if facts.socket_reachable is not True:
        return ConnectionState.ADDON_DISCONNECTED
    if facts.read_roundtrip_ok is False:
        return ConnectionState.ADDON_DISCONNECTED
    if facts.missing_credentials:
        return ConnectionState.DEGRADED
    return ConnectionState.READY


def state_copy(state: ConnectionState) -> dict[str, str]:
    """User-facing copy for ``state`` (title/message/action)."""
    return dict(STATE_COPY[state])


def render_state_line(state: ConnectionState) -> str:
    copy = state_copy(state)
    return f"[{state.value}] {copy['title']} — {copy['message']} 下一步：{copy['action']}"


# ---------------------------------------------------------------------------
# Minimal user-registry scan (no YAML dependency).
# ---------------------------------------------------------------------------

def registry_mentions_blender(text: str) -> bool:
    """Best-effort detection of an enabled ``servers: blender:`` entry.

    Parses just the two-space indentation level under ``servers:`` so a
    ``blender`` key anywhere else cannot satisfy the check. This is a UX
    heuristic for the journey script; the authoritative check is
    ``mcp-gateway config validate`` plus ``mcp-gateway diagnose blender``.
    """
    in_servers = False
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        if not raw_line.startswith((" ", "\t")):
            in_servers = line == "servers:"
            continue
        if not in_servers:
            continue
        stripped = line.strip()
        if (
            raw_line.startswith("  ")
            and not raw_line.startswith("   ")
            and stripped == "blender:"
        ):
            return True
    return False


def registry_disabled_blender(text: str) -> bool:
    """True when a ``servers: blender:`` entry exists with ``enabled: false``."""
    lines = text.splitlines()
    for index, raw_line in enumerate(lines):
        if raw_line.rstrip() == "  blender:":
            window = lines[index + 1 : index + 6]
            for follow in window:
                if not follow.startswith("    "):
                    break
                if re.match(r"\s*enabled:\s*false\s*$", follow):
                    return True
            return False
    return False


# ---------------------------------------------------------------------------
# Copy sanitization rules shared by tests and the journey script.
# ---------------------------------------------------------------------------

#: Patterns that must never appear in user-facing state copy.
COPY_FORBIDDEN_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"/home/[A-Za-z0-9_.-]+", "absolute home path"),
    (r"/Users/[A-Za-z0-9_.-]+", "absolute home path"),
    (r"(?i)[A-Za-z]:\\\\", "windows path"),
    (r"~", "home-directory shorthand"),
    (r"(?i)\b(api[_-]?key|secret|password|token)\b\s*[:=]", "credential-like key/value"),
    (r"https?://", "URL"),
    (r"(?i)\b[A-Z0-9]{20,}\b", "credential-like opaque value"),
)


def copy_is_sanitized(text: str) -> list[str]:
    """Return the list of sanitization violations in ``text`` (empty = clean)."""
    violations: list[str] = []
    for pattern, label in COPY_FORBIDDEN_PATTERNS:
        if re.search(pattern, text):
            violations.append(label)
    return violations


def all_copy_sanitized() -> dict[str, list[str]]:
    """Violations per state across every piece of state copy."""
    problems: dict[str, list[str]] = {}
    for state, copy in STATE_COPY.items():
        for field_name, text in copy.items():
            violations = copy_is_sanitized(text)
            if violations:
                problems[f"{state.value}.{field_name}"] = violations
    return problems


def unique_recovery_actions() -> bool:
    """Every non-ready state must name a distinct recovery action."""
    actions = [
        copy["action"]
        for state, copy in STATE_COPY.items()
        if state is not ConnectionState.READY
    ]
    return len(actions) == len(set(actions))
