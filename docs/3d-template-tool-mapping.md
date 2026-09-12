# `3d` 模板编译产物 → blender-mcp 工具执行映射

对应 change：`blender-mcp-yeisme-integration-v1` 任务 2.1。语义层归 `data/yeisme-prompt-templates`（`official-3d-model-templates-beta-v1`，5 个 solution）；本仓只拥有**执行映射**：把模板编译产物的字段翻译成对具体 MCP 工具的调用序列。模板正文不动。

对照基线：`data/yeisme-prompt-templates/solutions/3d/` 下的 `text-to-3d-object-beta`、`image-to-3d-refine-beta`、`3d-scene-layout-beta`、`3d-printable-design-beta`、`3d-asset-review-beta`（schema `promptrepo.solution.v0.1`，version `1.0.0-beta.1`）。

## 通用规则

- 模板编译（promptrepo 侧）**不做任何模型调用、不产生 3D 资产**；每个模板的 "Execution and evidence boundary" 都声明执行是另行授权的步骤。执行映射只在用户授权后生效。
- 工具分级沿用 `config/tool-classification.json`：映射到的 generate 工具默认不暴露（启用走[审批与费用门](./gateway/approvals-and-cost-gate.md)）；`execute_blender_code`（exec 级）不是任何模板的映射目标。
- 证据规则：凡模板要求 "not evaluated" 的字段，执行侧必须用真实工具往返取证后才能改判；取证一律用 read 工具。

## 五类映射

### 1. 文生 3D（`text-to-3d-object-beta`）

模板产物：provider-neutral 提示包（subject/purpose/style/constraints 已确认）。

| 模板字段 | 工具调用 |
| --- | --- |
| 提示包整体（text 生成路径） | `generate_hyper3d_model_via_text`（generate 级，需启用+审批）或 `generate_hunyuan3d_model`（text 分支） |
| 生成任务状态 | `poll_rodin_job_status` / `poll_hunyuan_job_status`（read） |
| 产物入库 | `import_generated_asset` / `import_generated_asset_hunyuan`（write） |
| Review checklist 取证 | `get_scene_info` + `get_object_info` + `get_viewport_screenshot`（read） |

说明：provider-neutral 提示包到 provider 参数的翻译由 agent 在调用时完成；本仓不实现 prompt 编译。选 Hyper3D 还是 Hunyuan3D 由用户/审批决定，两者互为备选。

### 2. 图生 3D（`image-to-3d-refine-beta`）

模板产物：多视角一致性声明、遮挡推断策略（`inference_marked`/`conservative_infer`/`visible_only`）、分离表、refine brief。

| 模板字段 | 工具调用 |
| --- | --- |
| 参考图输入（image 生成路径） | `generate_hyper3d_model_via_images`（generate 级）；单图场景可用 `generate_hunyuan3d_model` 的 image 分支 |
| 多视角/遮挡策略 | 作为生成调用的约束参数与 review 取证口径，不映射为独立工具 |
| Refinement brief（显式授权的后续 refine 步） | 迭代调用同一生成工具 + `import_generated_asset*` 后用 read 工具复测 |
| Separation table 复核 | `get_object_info`（结构声明 vs 实测）+ `get_viewport_screenshot`（视角核对） |

### 3. 场景布局（`3d-scene-layout-beta`）

模板产物：布局提案（物体清单、相对位置、相机/灯光意图）；模板明确「场景构建与 canonical spatial state 属于 owning systems」。

| 模板字段 | 工具调用 |
| --- | --- |
| 物体获取 | `search_polyhaven_assets` / `search_sketchfab_models` / `search_polypizza_models`（read）→ `download_*_asset/model`（write） |
| 布局落地 | addon 场景写操作组合：`set_texture`（材质）+ 上游 addon 场景命令（经 `execute_blender_code` 之外的既有工具面；本 change 不新增工具） |
| 布局取证 | `get_scene_info`（层级/变换实测）+ `get_viewport_screenshot` |
| Canonical spatial state | **无执行映射**：归 Scaena/Anatomia 等 owning systems，本仓不存 canonical state |

### 4. 打印约束（`3d-printable-design-beta`）

模板产物：可判定的约束清单（manifold、壁厚、支撑策略、公差、打印朝向）+ 单位纪律 + 失败分诊。

| 模板字段 | 工具调用 |
| --- | --- |
| 约束清单 | **映射为建模参数建议，不强制**：作为 `generate_*` 调用的约束输入与人工/工具复核口径，不自动判定 pass/fail |
| 单位纪律 | `get_scene_info`（场景单位实测取证） |
| 几何核查取证 | `get_object_info`（mesh 统计）；深度核查（manifold/壁厚量化）超出当前工具面，标注 "not evaluated" 待外部检查器 |
| 失败分诊 | 人工决策，无工具映射 |

### 5. 资产评审（`3d-asset-review-beta`）

模板产物：几何完整性 / UV 与贴图 / 尺度一致性 / 权利审查四段 pass-fail-unknown 评审。

| 模板字段 | 工具调用 |
| --- | --- |
| Geometry integrity | `get_object_info`（拓扑密度、退化几何迹象） |
| UV and texture | `get_object_info`（material slots/UV 数据）+ `get_viewport_screenshot`（拉伸/接缝目视） |
| Scale consistency | `get_scene_info` / `get_object_info`（维度实测）；无 scale anchor 时保持 unknown |
| Rights review（origin/license） | **无执行映射**：许可信息不在 Blender 场景数据里，由资产来源侧（PolyHaven/Sketchfab/PolyPizza 的 search 结果元数据）+ 人工记录承担；本仓不做权利判定 |
| Review header（asset reference） | `get_object_info` 按名核对 |

## 映射维护

- 模板侧新增/修改 solution 时：本表须同步评审（对照 `solutions/3d/` 清单），无映射的条目显式写「无执行映射」及原因，不许静默遗漏。
- 工具面变更（稳定工具名/参数）走 `yeisme-evolutionary-change-policy`；分级表与校验脚本保证上游新增工具不会绕过本表进入默认暴露面。
- DSH 工作台对映射的可视化消费归 `dsh-template-registry-integration-v1`（后续 change）。
