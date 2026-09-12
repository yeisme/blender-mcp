# Blender MCP Yeisme 集成设计

## 决策

1. **fork 复用，不自建**：上游（Python server + Blender addon）整体保留，Yeisme 改动以 additive 为主（分级元数据、配置示例、文档），不改上游工具语义。偏离仓内「独立 MCP 服务默认 Go」惯例，理由：用户明确 fork 复用决策，且 Blender 进程内代码只能 Python，自建 Go server 会失去上游 27 个工具与三个资产源、两个 3D 生成 provider 的现成集成。
2. **安全分级在 Gateway 层强制**：不改上游 server 代码来实现分级（避免与上游漂移），分级体现在 Gateway export profile 的 `exposeTools` 白名单与审批策略；fork 内只补分级元数据文档与校验脚本。`execute_blender_code` 默认不进任何 export profile。
3. **generate 类工具费用门**：`generate_hyper3d_model_via_*`、`generate_hunyuan3d_model` 产生外部 provider 调用与费用，凭据由用户自配，Gateway 审批开启前默认不暴露。

## 架构

```mermaid
flowchart LR
  subgraph Agent 侧
    DSH[DSH 模板工作台 / 任意 agent]
    GW[mcp/gateway<br/>namespace: blender<br/>export profile 白名单 + 审批]
  end
  subgraph 本机
    SRV[blender-mcp server<br/>stdio / uvx]
    ADD[Blender addon<br/>127.0.0.1:9876 loopback]
    BL[Blender]
  end
  EXT[PolyHaven / Sketchfab / PolyPizza<br/>Hyper3D Rodin / Hunyuan3D]
  DSH --> GW --> SRV --> ADD --> BL
  SRV -. 用户自配凭据 .-> EXT
  TPL[data/yeisme-prompt-templates<br/>3d 模板编译产物] -. 执行映射文档 .-> DSH
```

## 生态核实（2026-09-12，gh search repos）

- Blender：`ahujasid/blender-mcp` 28.3k stars / 2.6k forks / 2026-09-07 活跃，第二名仅 299 stars，确认为绝对事实标准。两个活跃差异化 fork 留作工具面扩展参考：`seehiong/blender-mcp-bridge`（93 工具）、`sandraschi/blender-mcp`（headless FastMCP，41 个组合工具）。
- UE（二期）：候选修正为 `ChiR24/Unreal_mcp`（866 stars，2026-09-11 活跃）；原首选 `chongdashu/unreal-mcp`（2077 stars）2025-04 后停更，仅作协议参考。二期立项时重新核实。

## Gateway 对接与用户体验

### registry 片段（脚本生成、脱敏）

```yaml
servers:
  blender:
    enabled: true
    transport: stdio
    command: uvx
    args: ["blender-mcp"]
    gateway:
      enabled: true
      namespace: blender
      exposeTools: [get_scene_info, get_object_info, get_viewport_screenshot, search_polyhaven_assets, download_polyhaven_asset, set_texture]  # read + 白名单 write；generate/exec 不在列
```

### First-run 用户旅程（7 步）

1. 安装 Blender（用户自装，文档给出受支持版本核对命令）。
2. `uvx blender-mcp` 可启动（`uv` 缺失时文档给出安装命令）。
3. Blender 内安装 addon 并点 Connect（上游既有流程，fork 文档本地化 + 截图）。
4. `mcp-gateway quickstart` 生成个人配置（不覆盖已有文件）。
5. 追加 blender server 片段（脚本生成，可粘贴）→ `mcp-gateway validate --registry ~/.mcp-gateway/registry.yaml`。
6. `mcp-gateway serve` 启动；`mcp-gateway status` 看到 blender namespace。
7. agent/DSH 接入：`mcp-gateway client config` 渲染客户端配置，`mcp-gateway client doctor` 检查就绪，`mcp-gateway client smoke` 协议冒烟。

### 连接状态模型与用户可见文案

| 状态 | 判定 | 用户看到 | 恢复动作 |
| --- | --- | --- | --- |
| not_configured | registry 无 blender 条目 | 「未配置 Blender 接入」+ 配置片段指引 | 走 first-run 4–5 |
| server_unreachable | stdio 拉起失败 | 「server 未就绪」+ `mcp-gateway diagnose blender` | 检查 uvx/安装 |
| addon_disconnected | server 在、socket 不通 | 「请在 Blender 中启动 addon 连接」（含菜单位置） | Blender 内 Connect |
| ready | read 工具往返成功 | 工具可用 | — |
| degraded | 部分资产源凭据缺失 | 对应 generate/download 入口禁用 + 原因 | 用户自配凭据 |

原则：每态只禁相关 mutation，诚实降级，不出现死按钮；DSH pane 只消费这些状态的 safe projection。

### 审批与费用 UX

- write 级（下载资产、改材质）：Gateway 审批一次一果，receipt 可查（`mcp-gateway approvals`）。
- generate 级（文生/图生 3D）：首次使用显式说明「将调用外部 provider 并产生费用」，用户确认 + 凭据就绪后才出现在工具面；审批文案含 provider 名与预计产物类型，不含凭据。
- exec 级：不出现在任何 profile；本地直连使用时由用户自行承担，文档明确风险。

### 诊断路径

`mcp-gateway diagnose blender`（后端诊断）→ `mcp-gateway doctor`（客户端就绪）→ `mcp-gateway tools`（工具面核对，比对分级表）。DSH 侧 `ui-mcp-inspector` 自动可见会话内 blender 工具活动。

## 工具分级（上游 27 个工具）

| 级别 | 工具 | Gateway 默认 |
| --- | --- | --- |
| read | `get_addon_status`、`get_scene_info`、`get_object_info`、`get_viewport_screenshot`、`get_polyhaven_categories`、`get_polyhaven_status`、`get_hyper3d_status`、`get_sketchfab_status`、`get_polypizza_status`、`search_polyhaven_assets`、`search_sketchfab_models`、`get_sketchfab_model_preview`、`search_polypizza_models`、`poll_rodin_job_status`、`poll_hunyuan_job_status` | 暴露 |
| write | `set_texture`、`download_polyhaven_asset`、`download_sketchfab_model`、`download_polypizza_model`、`import_generated_asset`、`import_generated_asset_hunyuan`、`record_trajectory_feedback`、`disable_telemetry` | 暴露，写操作记 receipt |
| generate | `generate_hyper3d_model_via_text`、`generate_hyper3d_model_via_images`、`generate_hunyuan3d_model` | 默认不暴露；启用需审批 + 用户凭据 |
| exec | `execute_blender_code` | 永不进 export profile；仅本地直连 + 显式授权 |

## 上游同步

- `main` 仅 fast-forward 跟踪 `upstream/main`；Yeisme 改动全在 `develop`。
- 同步节奏：随上游 release 或每月 `git fetch upstream && git merge upstream/main` 到 `develop`；冲突保留上游行为优先。
- 通用修复（安全、协议兼容）优先向上游开 PR；fork 内 carry patch 必须在上游 PR 链接登记。

## 模板执行映射

`3d` 模板编译产物（provider-neutral 提示包）到工具调用的映射规则：文生 3D → `generate_hyper3d_model_via_text`（或 Hunyuan3D）；图生 3D → `generate_hyper3d_model_via_images` + `import_generated_asset`；场景布局 → addon 场景写操作组合；打印约束 → 映射为建模参数建议（不强制）；评审清单 → `get_scene_info`/`get_object_info`/`get_viewport_screenshot` 取证。映射文档归 `docs/`，模板正文不动。

## 验证

- `uv run pytest` 全量通过（上游测试含 safe_mode、线程、unicode socket）。
- 分级元数据校验脚本：server 实际工具列表与分级表一致（新增上游工具未分级时 fail）。
- registry 示例由脚本生成且脱敏；`openspec validate --strict` 通过。
- 本机 Blender 集成 smoke（addon 连接、read 工具往返、viewport 截图）证据写 `temp/integration-test-runs/<run-id>/`，脱敏。

## 外部阶段

generate 类工具的真实 provider 调用与费用、DSH 工作台接线（依赖 `dsh-template-registry-integration-v1`）、UE fork（`mcp/unreal-mcp`，二期）均另行立项与授权。
