# Blender MCP（Yeisme fork）子项目指令

本仓是 `ahujasid/blender-mcp` 的 Yeisme fork（MIT），定位为 Yeisme agent 体系的**通用 AI 3D 建模执行层**：agent 经 MCP 调用本 server，server 经 loopback socket 驱动用户本机 Blender addon 完成建模、材质、相机灯光与渲染预览。

分工边界：本仓拥有 Blender 建模执行与工具面；Prompt 语义层归 `data/yeisme-prompt-templates`（`3d` 类别）；影视复刻 canonical 资产归 Scaena/Anatomia；统一接入与审批归 `mcp/gateway`；DSH 交互外壳归 `agent/harness-plugins`。本仓不实现 prompt 编译、不存领域资产 canonical state、不做调度/审批平台。

## 技术栈

- Python >= 3.10，`uv` 管理依赖；MCP SDK `mcp>=1.9,<2`；`httpx`。
- `src/blender_mcp/server.py`：MCP server（stdio）；`addon.py`：Blender 进程内 socket server（默认 `127.0.0.1:9876`）。
- 运行：`uvx blender-mcp` 或 `uv run blender-mcp`；Blender 侧安装 addon 并启动连接。

## Fork 与上游同步政策

- `main` 跟踪上游 `https://github.com/ahujasid/blender-mcp.git`（remote `upstream`），不在 `main` 上提交 Yeisme 改动。
- `develop` 是 Yeisme 集成分支：加固、文档、OpenSpec 与集成都提交到这里。
- 上游同步：`git fetch upstream && git merge upstream/main`（或 rebase）到 `develop`，冲突优先保留上游行为，Yeisme 改动以 additive 为主。
- 保留 MIT LICENSE 与上游作者署名；不改写已发布历史。
- 上游已接受且 Yeisme 也需要的通用修复，优先向上游开 PR，fork 内只做短期 carry patch。

## 边界与禁止事项

- socket 仅绑定 loopback；不增加远程监听、鉴权 token 文件或远端资产自动下载到默认路径之外的位置。
- `execute_blender_python`（任意代码执行）是最高危工具：默认不在 Gateway export profile 暴露；仅本地直连 + 显式授权可用。新增工具必须标注 read/write/exec 分级。
- 不在源码、fixture、日志、证据中写入凭据、token、绝对用户路径、raw provider payload。
- 不 vendor 大体积二进制资产进仓；示例场景用最小文件或生成脚本。
- 结构化 metadata（openspec、registry 示例）用 CLI/脚本生成，不手写。

## 测试与质量门禁

```bash
uv sync
uv run pytest
uv run python scripts/verify_tool_classification.py        # 分级表 vs server 实际工具
uv run python scripts/generate_gateway_registry_example.py --check   # 示例与分级表同步
uv run ruff check src tests 2>/dev/null || true   # 上游未配 lint 时不强制
```

集成验证（需要本机 Blender）：安装 addon → 启动连接 → `uvx blender-mcp` stdio smoke → 记录脱敏证据到 `temp/integration-test-runs/<run-id>/`。

## Skill 路由

- 本仓 active skills 由根 `.skills/profiles/targets/mcp/blender-mcp.txt` 声明，`scripts/skills.sh sync-target mcp/blender-mcp` 生成双 runtime。
- Gateway 注册/审批/export profile 用 `yeisme-mcp-gateway-provider` 与 `yeisme-mcp-registry-onboarding`；消费方诊断用 `yeisme-mcp-gateway-consumer`。
- 稳定工具名、参数、错误码变更用 `yeisme-evolutionary-change-policy`。
