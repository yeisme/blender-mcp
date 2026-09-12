# Blender MCP 文档导航

- [上游 README](../README.md)：安装、Claude/Cursor 接入、PolyHaven/Hyper3D/Sketchfab 集成说明（英文，上游维护）。
- [Yeisme fork 指令](../AGENTS.md)：fork 同步政策、安全分级、质量门禁。
- [Gateway 接入 first-run 旅程与五态状态模型](./gateway/first-run-journey.md)：七步旅程、状态判定脚本、诊断路径。
- [审批与费用门](./gateway/approvals-and-cost-gate.md)：generate 类工具启用流程、receipt 与费用追溯。
- [Gateway registry 示例](./gateway/registry-blender-example.yaml)：脚本生成的脱敏示例（勿手改，用 `scripts/generate_gateway_registry_example.py` 再生）。
- [`3d` 模板执行映射](./3d-template-tool-mapping.md)：prompt-templates 五类 solution → 工具调用映射。
- [上游同步 Runbook](./upstream-sync.md)：同步步骤、dry-run、冲突原则、carry patch 登记。
