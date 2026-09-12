# 审批与费用门：generate 类工具启用流程

对应 change：`blender-mcp-yeisme-integration-v1` 任务 1.3。分级定义见 `config/tool-classification.json` 与 `src/blender_mcp/tool_classification.py`；默认 export profile 见 [registry-blender-example.yaml](./registry-blender-example.yaml)（脚本生成，勿手改）。

## 分级与默认暴露

| 级别 | 工具 | Gateway 默认 |
| --- | --- | --- |
| read（16） | `get_*`、`search_*`、`poll_*` | 暴露 |
| write（8） | `set_texture`、`download_*`、`import_generated_asset*`、`record_trajectory_feedback`、`disable_telemetry` | 暴露（默认 profile 含 curated 2 个：`download_polyhaven_asset`、`set_texture`；其余 write 可由用户自行加入，受 20 个 public tool 上限约束） |
| generate（3） | `generate_hyper3d_model_via_text`、`generate_hyper3d_model_via_images`、`generate_hunyuan3d_model` | 不暴露；启用需审批 + 用户自配凭据 |
| exec（1） | `execute_blender_code` | 永不进任何 export profile；仅本地直连 + 显式授权 |

默认 profile 的排除效果（离线实测，2026-09-12）：

```console
$ mcp-gateway policy test --tool blender_generate_hunyuan3d_model --user user-1 \
    --registry docs/gateway/registry-blender-example.yaml --json
"code": "policy_test_failed",
"message": "tool name must be a public gateway tool name: blender_generate_hunyuan3d_model",

$ mcp-gateway policy test --tool blender_execute_blender_code --user user-1 \
    --registry docs/gateway/registry-blender-example.yaml --json
"code": "policy_test_failed",

$ mcp-gateway policy test --tool blender_set_texture --user user-1 \
    --registry docs/gateway/registry-blender-example.yaml --json
"decision": "allow", "reason": "matched public allowlist", "approval_required": false,
```

## generate 类启用流程（一次性，用户主导）

1. **用户自配凭据**：在 Blender 内 `Edit → Preferences → Add-ons → Blender MCP` 的偏好设置中填入用户自己的 provider API key（Hyper3D / Hunyuan3D）。凭据只存在用户本机 Blender 配置中；也可用环境变量 `BLENDERMCP_HYPER3D_API_KEY` 等（见 `config/tool-classification.json` 的 `providerCredentialEnvVars`）。本仓与 Gateway 均不存储、不转发凭据。
2. **用户显式确认费用**：首次启用前，用户必须看到并确认「将调用外部 provider 并产生费用」。确认后由用户在自己的用户级注册表（`~/.mcp-gateway/registry.yaml`，不入仓）把 generate 工具加入 blender 条目的 `exposeTools`。**仓库内示例永远不含 generate 工具**：生成脚本对 generate/exec 工具有硬断言（`assert_exportable`）。
3. **审批门**：workspace 策略要求该工具调用须审批：
   ```bash
   mcp-gateway policy apply --file <workspace-policy.json>   # 策略归 mcp/gateway 定义
   mcp-gateway approvals list                                # 查看待审批
   mcp-gateway approvals show appr_01J...                    # 看一条审批详情
   mcp-gateway approvals decide appr_01J... --decision approved   # 或 rejected
   ```
   审批文案必须含 provider 名（Hyper3D Rodin / Hunyuan3D）与预计产物类型（mesh/glb 文件），**不含凭据**。
4. **receipt 与费用追溯**：
   ```bash
   mcp-gateway audit list          # 审计事件摘要（含 write/generate 调用 receipt）
   mcp-gateway budget status       # run 级 token/费用控制摘要
   ```
   write 级（下载资产、改材质）审批一次一果：每次调用产生独立 receipt，可由 `audit list` 追溯。

以上 CLI 均已在本机核验可运行（未启动 Gateway 时会得到诚实的 loopback connection refused 提示，如 `Suggestion: confirm the Gateway service is running`），完整审批闭环需要 `mcp-gateway serve` 运行中的本机 Gateway。

## exec 级：永不经 Gateway

`execute_blender_code`（任意 Blender 内 Python 执行）是最高危工具：

- 生成器断言使其无法进入任何脚本生成的 export profile；
- 校验脚本（`scripts/verify_tool_classification.py`）保证分级表始终把它标为 `exec`；
- 本地直连使用时由用户自行承担风险：该工具可执行任意代码、读写本机文件。文档与 DSH 侧均不得把它作为推荐路径。

## 状态联动

generate/download 入口的可用性受连接状态模型约束（见 [first-run-journey.md](./first-run-journey.md)）：`degraded` 态只禁对应资产源的 mutation 入口并给出原因，其余工具照常可用。
