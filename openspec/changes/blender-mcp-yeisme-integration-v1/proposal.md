## Why

Yeisme agent 体系需要通用 AI 3D 建模执行层，配合 prompt-templates 仓在途的 `3d` 模板类别（`official-3d-model-templates-beta-v1`）与 DSH 集成（`dsh-template-registry-integration-v1`）。用户已决定：开源项目有就尽量复用，fork 开发，不从零自建。`ahujasid/blender-mcp` 是该领域事实标准（MIT、活跃、28k stars），且上游已自带 PolyHaven/Sketchfab/PolyPizza 资产源与 Hyper3D Rodin、腾讯 Hunyuan3D 的文生/图生 3D 生成工具，直接覆盖 `text-to-3d-object-beta`、`image-to-3d-refine-beta` 的执行需求。本 fork 已就位（`yeisme/blender-mcp`，`develop` 为集成分支），本 change 定义加固与集成工作。

## What Changes

- 工具面安全分级落地：为上游 27 个工具标注 read/write/generate/exec 四级，Gateway export profile 默认只暴露 read + 部分 write；`execute_blender_code` 与 generate 类（产生 provider 费用）默认不暴露或走显式审批。
- Gateway 集成：registry 示例（脱敏、脚本生成）、export profile、审批策略与运维文档；真实运行配置只放用户级 `~/.mcp-gateway/registry.yaml`。
- 与模板仓库的衔接：文档化 `3d` 模板编译产物到 blender-mcp 工具调用的映射（prompt 语义层不动，执行映射归本仓）。
- 上游同步流程落地：`main` 跟踪 upstream、`develop` 承载 Yeisme 改动、通用修复优先回上游。
- DSH 下游接线声明为依赖 `dsh-template-registry-integration-v1` 的后续工作，不在本 change 实现。

## Capabilities

### New Capabilities

- `blender-mcp-yeisme-integration`：fork 安全分级、Gateway 注册与审批、模板执行映射与上游同步。

### Modified Capabilities

无。

## Impact

改动范围限于本 fork 的 `develop` 分支：安全分级元数据、Gateway 配置示例与文档、OpenSpec；不修改上游工具行为语义，不引入新 provider 依赖，不产生费用（generate 类工具须用户显式启用并自配凭据）。`main` 保持跟踪上游。文档修改、构建发布与远端部署分别报告。
