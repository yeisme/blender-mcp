# Blender 接入 First-run 旅程与连接状态模型

对应 change：`blender-mcp-yeisme-integration-v1` 任务 1.4。本仓只做 Blender 建模执行层；统一接入、审批与配置归 `mcp/gateway`。所有命令只访问本机（loopback），不接触外部服务，不读取任何凭据值。

## 七步旅程

1. **安装 Blender**（用户自装）。受支持版本核对：Blender 内 `Blender → About Blender`，或在系统包管理器中查询 `blender` 版本；addon 需要支持 Python 3.10+ 的 Blender 4.x。
2. **确认 server 可启动**：
   ```bash
   uv --version || echo "uv 未安装：见 https://docs.astral.sh/uv/getting-started/install/"
   uv run blender-mcp --help
   ```
   `--help` 由 addon 安装 CLI 处理并立即退出——它证明 server 包可以本地拉起，不会连接任何外部服务。
3. **在 Blender 中安装 addon 并连接**（上游既有流程）：下载/更新 addon 后在 Blender 中 `Edit → Preferences → Add-ons → Install...` 选择 `addon.py`（或运行 `uvx blender-mcp install-addon`），启用 `Interface: Blender MCP`，点击 `Start MCP Server`。截图指引见[上游 README](../README.md#installation)。
4. **生成个人 Gateway 配置**（不覆盖已有文件）：
   ```bash
   mcp-gateway quickstart
   ```
5. **追加 blender server 片段并校验**（片段由脚本生成，可粘贴）：
   ```bash
   uv run python scripts/blender_first_run.py snippet
   mcp-gateway config validate --registry ~/.mcp-gateway/registry.yaml
   ```
6. **启动并确认 namespace**：
   ```bash
   mcp-gateway serve
   mcp-gateway status --registry ~/.mcp-gateway/registry.yaml
   ```
7. **客户端接入**：
   ```bash
   mcp-gateway client config
   mcp-gateway client doctor
   mcp-gateway client smoke
   ```

## 状态判定脚本

```bash
uv run python scripts/blender_first_run.py state --json          # 机器可读
uv run python scripts/blender_first_run.py state                 # 人读单行
uv run python scripts/blender_first_run.py state --probe-roundtrip  # 追加 read 工具往返
```

脚本按序探测：用户注册表（默认 `~/.mcp-gateway/registry.yaml`，`--registry` 可覆盖）→ stdio server 本地拉起 → loopback addon socket（`127.0.0.1:9876`，`BLENDER_HOST`/`BLENDER_PORT` 可覆盖，仅允许 loopback）→（可选）MCP stdio read 工具往返。退出码：`0` = ready，`2` = 非 ready。

## 五态连接状态模型

判定顺序自上而下，`None`（未探测）一律保守处理：ready 只建立在正向证据上。

| 状态 | 判定 | 用户看到 | 恢复动作（唯一） |
| --- | --- | --- | --- |
| `not_configured` | registry 无 blender 条目（含文件不存在） | 「Blender 接入未配置——个人 Gateway 配置中还没有 blender server 条目。」 | 走旅程第 4–5 步：生成个人配置后粘贴片段 |
| `server_unreachable` | stdio server 拉起失败（含 uv 缺失） | 「Blender server 未就绪——stdio 方式拉起 blender-mcp server 失败，通常是 uv 或安装缺失。」 | 按文档安装 uv 后重试，或运行 `mcp-gateway diagnose blender` |
| `addon_disconnected` | server 在、socket 不通（或 read 往返失败） | 「请在 Blender 中启动 addon 连接——本机 loopback 端口上没有 Blender addon 在监听。」 | Blender 内 `Preferences → Add-ons → Blender MCP` 点击 `Start MCP Server` |
| `ready` | read 往返成功（socket+server 正向证据） | 「Blender 接入就绪——read 工具往返成功，全部暴露工具可用。」 | 无 |
| `degraded` | 核心可用但部分资产源凭据缺失 | 「Blender 接入可用（部分资产源未配置）——未配置凭据的资产源的 generate/download 入口被禁用。」 | 在 Blender addon 设置中为对应资产源填写用户自己的凭据后重启连接 |

原则：每态只禁相关 mutation，诚实降级，不出现死按钮；状态文案不含文件路径与凭据（由 `tests/test_first_run.py` 强制）。DSH pane 只消费这些状态的 safe projection（后续 change）。

## 诊断路径

后端诊断 → 客户端就绪 → 工具面核对：

```bash
mcp-gateway diagnose --backend blender --registry ~/.mcp-gateway/registry.yaml
mcp-gateway doctor
mcp-gateway tools list --registry ~/.mcp-gateway/registry.yaml
```

`tools list` 的输出与 `config/tool-classification.json` 的 `defaultExportTools` 比对：多出的工具说明 profile 被人为放宽，须回查分级表；`generate_*`/`execute_blender_code` 出现即为违规（见 [审批与费用门](./approvals-and-cost-gate.md)）。

## 实测记录（2026-09-12，无 Blender 环境，脱敏）

```console
$ uv run python scripts/blender_first_run.py snippet
servers:
  blender:
    enabled: true
    description: Local Blender execution backend (loopback addon socket); read + curated write tools only, generate/exec excluded by the generator
    transport: stdio
    command: uvx
    args: [blender-mcp]
    gateway:
      enabled: true
      namespace: blender
      exposeTools:
        - download_polyhaven_asset
        ...（read 16 + curated write 2，完整清单见 registry-blender-example.yaml）

$ uv run python scripts/blender_first_run.py state --registry <absent.yaml>
[not_configured] Blender 接入未配置 — 个人 Gateway 配置中还没有 blender server 条目。 下一步：运行旅程第 4–5 步：先生成个人 Gateway 配置，再粘贴 blender server 配置片段。
诊断路径: mcp-gateway diagnose blender → mcp-gateway doctor → mcp-gateway tools
(exit 2)

$ uv run python scripts/blender_first_run.py state --registry <configured.yaml>
[addon_disconnected] 请在 Blender 中启动 addon 连接 — blender-mcp server 已就绪，但本机 loopback 端口上没有 Blender addon 在监听。 下一步：在 Blender 中打开 Preferences → Add-ons → Blender MCP，点击 Start MCP Server。
诊断路径: mcp-gateway diagnose blender → mcp-gateway doctor → mcp-gateway tools
(exit 2)

$ mcp-gateway diagnose --backend blender --registry <configured.yaml>
Error: Post "http://127.0.0.1:8080/v1/diagnostics": dial tcp 127.0.0.1:8080: connect: connection refused
Suggestion: confirm the Gateway service is running
```

`ready`/`degraded` 两态在本环境不可达（需真实 Blender addon 连接），由 `tests/test_first_run.py::test_all_five_states_reachable` 等单测覆盖判定逻辑；真机证据归任务 3.1（`temp/integration-test-runs/`）。

## 后续衔接

- DSH 工作台接线：依赖 `dsh-template-registry-integration-v1`，另行立项。
- generate 类真实调用与费用授权：见 [审批与费用门](./approvals-and-cost-gate.md)。
