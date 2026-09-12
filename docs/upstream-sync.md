# 上游同步 Runbook 与 Carry Patch 登记

对应 change：`blender-mcp-yeisme-integration-v1` 任务 2.2。政策见 [AGENTS.md](../AGENTS.md)：`main` 只跟踪上游 `ahujasid/blender-mcp`（remote `upstream`），`develop` 承载全部 Yeisme 改动（additive 为主），通用修复优先回上游。

## 同步节奏

随上游 release 或每月一次，执行「同步日」流程。

## 同步步骤

```bash
# 1) 前置检查（在任何写操作前）
git status --porcelain                # 必须为空
git branch --show-current             # 确认在 develop
git log --oneline -1 main             # 确认 main 未漂移（只跟踪 upstream）

# 2) 抓取上游（需要网络；由操作者执行）
git fetch upstream

# 3) main 只做 fast-forward 跟踪
git push origin upstream/main:main    # 或本地：git branch -f main upstream/main（禁止在 main 上产生非上游提交）

# 4) dry-run：先看冲突，不动工作树、不切分支
git merge-tree --write-tree --name-only develop upstream/main
#   退出码 0 = 干净；1 = 有冲突（输出列出冲突文件）
#   输出首行是合并后 tree OID，随后是冲突文件清单

# 5) 正式合并到 develop
git merge upstream/main
#   冲突处理原则：保留上游行为优先；Yeisme 改动重新以 additive 方式补回

# 6) 同步后门禁
uv sync && uv run pytest
uv run python scripts/verify_tool_classification.py
#    ↑ 上游新增未分级工具时此脚本 fail，合入被阻止（任务 1.1 的闸门）
uv run python scripts/generate_gateway_registry_example.py --check

# 7) 提交并推送（操作者执行）
```

## Dry-run 记录（2026-09-12）

本仓 clone 中 `upstream/*` 引用尚未抓取（抓取需网络），用 `origin/main`（fork 镜像的上游 main）做本地等价演练：

```console
$ git rev-list --left-right --count origin/main...develop
0	2            # develop 领先 2 个 Yeisme 提交、落后 0 → 无待合并上游内容

$ git merge-base origin/main develop
5f8ddaf ... docs: add codex instructions to README   # == origin/main HEAD

$ git merge-tree --write-tree --name-only develop origin/main
60fea92e390ab3cb05272082f44dae65b4b3c3f6            # 仅 tree OID，无冲突文件，exit 0
```

结论：对当前上游内容（`origin/main` = 5f8ddaf）dry-run 合并**零冲突**。develop 领先的 2 个提交（f4140ae、4ecb55e）全部是 additive 的文档/OpenSpec 改动，未触碰上游源码路径，与上游演进解耦。带真实 `upstream/main` 的 dry-run 在下次同步日执行（步骤 2 之后）。

## 冲突处理原则

1. 上游行为优先：上游改动的语义以 upstream 为准，Yeisme 侧让步后重新 additive 补齐（分级表、脚本、文档均为新增文件或独立目录，正常情况下不与上游路径相交）。
2. `pyproject.toml`/`uv.lock` 冲突：保留上游版本号与依赖，再重放 Yeisme 的 dev 依赖组。
3. `src/blender_mcp/server.py` 冲突：整块采用上游，随后跑 `scripts/verify_tool_classification.py` 重新分级新增工具。
4. 无法机械解决的：停下来在本文件登记冲突清单与决策，再继续。

## Carry Patch 登记

fork 内每个非上游提交（或补丁集）须登记；「上游 PR」列留空表示尚未开 PR。通用修复（安全、协议兼容）必须优先尝试回上游，fork 内只做短期 carry。

| Commit（develop） | 内容 | 性质 | 上游 PR | 状态 |
| --- | --- | --- | --- | --- |
| f4140ae | fork 引导：AGENTS/CLAUDE 指令 + openspec 加固 change | Yeisme 专属，不回上游 | —（无需） | 永久 carry |
| 4ecb55e | gateway onboarding journey / state model / 生态核实 | Yeisme 专属，不回上游 | —（无需） | 永久 carry |
| （后续） | 上游也适用的通用修复 | 候选回上游 | 待开 | 短期 carry |

登记规则：新增 carry patch 时同步加行；上游 PR 合并后该行改为「已回上游（PR #n），carry 可移除」。`main` 分支提交前必须满足 `git log upstream/main..main` 为空。

## 验证清单（每次同步后）

- [ ] `uv run pytest` 全绿
- [ ] `scripts/verify_tool_classification.py` 通过（新工具已分级）
- [ ] `scripts/generate_gateway_registry_example.py --check` 通过（示例与分级表同步）
- [ ] `openspec validate blender-mcp-yeisme-integration-v1 --strict --no-interactive`（或归档后 validate --all）
- [ ] carry patch 登记表更新
