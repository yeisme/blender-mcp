## ADDED Requirements

### Requirement: 工具安全分级
系统 SHALL 为上游全部 MCP 工具维护机器可读的 read/write/generate/exec 四级分级表，并提供校验脚本保证分级表与 server 实际注册工具一致。

#### Scenario: 上游新增工具未分级
- **WHEN** 上游同步引入新工具且分级表未更新
- **THEN** 校验脚本 fail 并列出未分级工具，合入被阻止

#### Scenario: exec 工具不经 Gateway 暴露
- **WHEN** 任意 Gateway export profile 生成或更新
- **THEN** `execute_blender_code` 不出现在 `exposeTools` 白名单

### Requirement: Gateway 注册与费用门
系统 SHALL 提供脚本生成的脱敏 registry 示例与 export profile，默认暴露 read 与 write 级工具，generate 级工具须显式审批与用户自配凭据后方可启用。

#### Scenario: 默认 profile 不含计费工具
- **WHEN** 使用默认 export profile 注册 blender namespace
- **THEN** `generate_hyper3d_model_via_text`、`generate_hyper3d_model_via_images`、`generate_hunyuan3d_model` 不可被 consumer 调用

#### Scenario: 运行配置不入仓
- **WHEN** 检查仓库内容
- **THEN** 不存在真实 endpoint、凭据源或 token；运行配置仅在用户级 `~/.mcp-gateway/registry.yaml`

### Requirement: 模板执行映射
系统 SHALL 文档化 prompt-templates `3d` 类别模板编译产物到本 server 工具调用的映射规则，覆盖文生 3D、图生 3D、场景布局、打印约束与资产评审五类。

#### Scenario: 映射覆盖全部在途 solution
- **WHEN** 对照 `official-3d-model-templates-beta-v1` 的 5 个 solution
- **THEN** 每个 solution 都有对应工具调用映射或显式标注「无执行映射」及原因

### Requirement: 上游同步纪律
系统 SHALL 保持 `main` 只跟踪上游、`develop` 承载 Yeisme 改动，通用修复优先回上游，fork 内 carry patch 登记上游 PR 链接。

#### Scenario: Yeisme 改动位置
- **WHEN** 提交 Yeisme 集成分支之外的改动
- **THEN** `main` 不含非上游提交；carry patch 均有登记

### Requirement: 集成边界
系统 SHALL 保持本 fork 只做 Blender 建模执行：不实现 prompt 编译、不存领域资产 canonical state、不做调度或审批平台。

#### Scenario: 证据与日志脱敏
- **WHEN** 产生集成证据或运行日志
- **THEN** 不含凭据、token、绝对用户路径或 raw provider payload

### Requirement: 对接用户旅程与状态可见性
系统 SHALL 提供脚本化的 first-run 对接旅程（安装核对、配置片段生成、validate、serve、client doctor/smoke）与五态连接状态模型（not_configured/server_unreachable/addon_disconnected/ready/degraded），每态给用户可见的下一步恢复动作。

#### Scenario: 每态可恢复
- **WHEN** 连接处于任意非 ready 状态
- **THEN** 用户可见原因与唯一明确的恢复动作；只禁相关 mutation，不出现死按钮

#### Scenario: generate 首次使用费用提示
- **WHEN** generate 级工具首次被启用
- **THEN** 用户看到「将调用外部 provider 并产生费用」的显式说明，确认且凭据就绪后工具才出现；审批文案不含凭据
