# 实施与验收任务

- [x] 1.1 工具分级元数据：为上游全部工具建立 read/write/generate/exec 分级表（机器可读），附校验脚本比对 server 实际注册工具；依赖无；验证上游新增未分级工具时脚本 fail；失败重检工具枚举来源。 | evidence: 分级校验脚本通过；未分级工具用例 fail
- [x] 1.2 Gateway export profile 与 registry 示例：脚本生成脱敏示例（namespace `blender`、read+write 白名单、generate/exec 排除）；依赖 1.1；验证示例通过 gateway registry schema 校验；失败重检 schema 字段。 | evidence: 示例生成脚本输出通过 schema 校验
- [x] 1.3 审批与费用门文档：generate 类工具启用流程（用户凭据、审批、receipt）；依赖 1.2；验证文档命令真实可运行；失败重检命令与实际 CLI 输出。 | evidence: docs 合入，命令经实际执行核对
- [x] 1.4 First-run 旅程脚本与状态模型落地：配置片段生成脚本、五态状态判定与用户文案（not_configured/server_unreachable/addon_disconnected/ready/degraded）、诊断路径（`diagnose`/`doctor`/`tools` 比对分级表）；依赖 1.2；验证每态有唯一恢复动作且文案不含路径/凭据；失败重检状态判定顺序。 | evidence: 五态测试用例通过；旅程命令逐步实测记录
- [x] 2.1 模板执行映射文档：`3d` 模板 → 工具调用映射规则（文生/图生/场景/打印/评审五类）；依赖无；验证映射覆盖 prompt-templates `official-3d-model-templates-beta-v1` 全部 5 个 solution；失败重检 solution 清单。 | evidence: docs/ 映射文档覆盖 5 solution
- [x] 2.2 上游同步流程演练：记录 `main` 跟踪、`develop` 合并、冲突处理与 carry patch 登记格式；依赖无；验证一次 dry-run 同步（无冲突或冲突解决记录）；失败重检 remote 配置。 | evidence: 同步 runbook + dry-run 记录
- [ ] 3.1 本机 Blender 集成 smoke：addon 安装连接、read 工具往返、viewport 截图；依赖 1.1；验证脱敏证据完整；失败重检 addon 版本匹配。 | evidence: temp/integration-test-runs/<run-id>/ 脱敏证据
- [x] 3.2 `uv run pytest` 全量门禁 + 新增校验脚本纳入；依赖 1.1；验证 CI 可复现命令；失败重检环境差异。 | evidence: pytest 全绿
- [x] 4.1 后续衔接（不阻塞本 change 关闭）：DSH 工作台接线（依赖 `dsh-template-registry-integration-v1`）、generate 类真实调用与费用授权、UE fork 二期立项，各自独立 change。
