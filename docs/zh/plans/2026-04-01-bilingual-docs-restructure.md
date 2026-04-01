# 双语文档重构实施计划

> **对 Claude 的要求：** 实施此计划时，需要按任务逐项推进，而不是一次性混改。

**目标：** 把仓库重构为以 `docs/` 作为双语最终产物区的结构，其中中英文技术博客与附录采用镜像布局，而 `reports/` 继续保持单语过程输出。

**架构思路：** 保留现有模块文档和调用链证据结构，同时在更高层引入“主文 + 附录”的博客化组织方式。`docs/zh/` 和 `docs/en/` 作为最终产物树，未来所有稳定结论都应在这两棵树里成对维护。

**技术栈：** Markdown、git、shell 目录迁移、Codex 编辑流程，以及本仓库现有的分析文档。

---

### 任务 1：固化已确认的目标结构

**文件：**
- 创建：`docs/plans/2026-04-01-bilingual-docs-restructure.md`

**步骤 1：记录目标结构**

计划中需要明确：

- `docs/zh/` 与 `docs/en/` 是镜像的最终产物树
- `reports/` 保持单语
- 采用“主文 + 附录”的混合博客模型

**步骤 2：确认迁移范围**

列出当前 `docs/` 中需要迁入双语树的正式文档。

**步骤 3：提交**

```bash
git add docs/plans/2026-04-01-bilingual-docs-restructure.md
git commit -m "docs: add bilingual docs restructuring plan"
```

### 任务 2：创建镜像的 `docs/zh` 与 `docs/en` 骨架

**文件：**
- 创建：`docs/zh/`
- 创建：`docs/en/`
- 创建：`docs/zh/blog/`
- 创建：`docs/en/blog/`
- 创建：`docs/zh/modules/`
- 创建：`docs/en/modules/`
- 创建：`docs/zh/callflows/`
- 创建：`docs/en/callflows/`
- 创建：`docs/zh/version-notes/`
- 创建：`docs/en/version-notes/`
- 创建：`docs/zh/plans/`
- 创建：`docs/en/plans/`

**步骤 1：先建立目录树**

先创建所有目标目录，再做文档迁移。

**步骤 2：验证目录树**

运行：

```bash
find docs -maxdepth 3 -type d | sort
```

预期：同时出现 `docs/zh/...` 和 `docs/en/...` 两套目录族。

**步骤 3：提交**

```bash
git add docs
git commit -m "docs: create bilingual docs directory layout"
```

### 任务 3：把现有正式文档迁入最终树

**文件：**
- 修改/迁移：`docs/overview.md`
- 修改/迁移：`docs/repo-map.md`
- 修改/迁移：`docs/architecture.md`
- 修改/迁移：`docs/analysis-rules.md`
- 修改/迁移：`docs/modules/*.md`
- 修改/迁移：`docs/callflows/*.md`
- 修改/迁移：`docs/version-notes/vX.Y.Z.md`
- 修改/迁移：`docs/plans/*.md`

**步骤 1：建立语言镜像**

保留现有正式文档内容，并把它们迁入新的语言树中。

**步骤 2：补上博客主文骨架**

创建：

- `docs/zh/blog/opencode-deep-dive.md`
- `docs/en/blog/opencode-deep-dive.md`

它们需要遵循已经确认的混合型博客结构。

**步骤 3：验证最终文档树**

运行：

```bash
find docs/zh -maxdepth 3 -type f | sort
find docs/en -maxdepth 3 -type f | sort
```

预期：所有正式文档都已落入新的语言树中。

**步骤 4：提交**

```bash
git add docs
git commit -m "docs: restructure finalized docs into bilingual trees"
```

### 任务 4：补齐镜像内容

**文件：**
- `docs/en/overview.md`
- `docs/en/repo-map.md`
- `docs/en/architecture.md`
- `docs/en/analysis-rules.md`
- `docs/en/blog/opencode-deep-dive.md`
- `docs/en/modules/*.md`
- `docs/en/callflows/*.md`
- `docs/en/version-notes/vX.Y.Z.md`
- `docs/en/plans/*.md`
- `docs/zh/overview.md`
- `docs/zh/repo-map.md`
- `docs/zh/architecture.md`
- `docs/zh/analysis-rules.md`
- `docs/zh/blog/opencode-deep-dive.md`
- `docs/zh/modules/*.md`
- `docs/zh/callflows/*.md`
- `docs/zh/version-notes/vX.Y.Z.md`
- `docs/zh/plans/*.md`

**步骤 1：保持文件集一致**

保证任一语言树中出现的正式文档，在另一侧都存在同路径文件。

**步骤 2：保持结构与锚点一致**

对每一对镜像文件：

- 保持章节顺序一致
- 保持核心结论一致
- 保持代码锚点一致
- 用自然语言重写内容，而不是逐句硬翻

**步骤 3：验证镜像完整性**

运行：

```bash
comm -3 <(cd docs/zh && find . -type f | sort) <(cd docs/en && find . -type f | sort)
```

预期：没有输出。

**步骤 4：提交**

```bash
git add docs
git commit -m "docs: complete bilingual final-output mirrors"
```

### 任务 5：更新仓库规则与任务路径

**文件：**
- 修改：`README.md`
- 修改：`AGENTS.md`
- 修改：`tasks/00-analysis-master-plan.md`
- 修改：`tasks/01-repo-inventory.md`
- 修改：`tasks/02-core-abstractions.md`
- 修改：`tasks/03-entrypoints.md`
- 修改：`tasks/04-high-level-callflow.md`
- 修改：`tasks/05-config-system.md`
- 修改：`tasks/06-provider-system.md`
- 修改：`tasks/07-tool-system.md`
- 修改：`tasks/08-runtime-orchestration.md`
- 修改：`tasks/09-memory-session.md`
- 修改：`tasks/10-ui-cli.md`
- 修改：`tasks/11-plugin-skill-system.md`
- 修改：`tasks/12-end-to-end-callflow.md`
- 修改：`tasks/13-open-questions.md`

**步骤 1：更新根说明**

让 `README.md` 和 `AGENTS.md` 明确说明：

- `docs/zh` 与 `docs/en` 是镜像的最终产物
- 正式文档更新应成对维护
- `reports/` 保持单语

**步骤 2：更新任务输出路径**

把任务文件中的最终输出路径从旧的平面 `docs/` 改成新的双语路径约定。

**步骤 3：提交**

```bash
git add README.md AGENTS.md tasks
git commit -m "docs: update workflow for bilingual finalized docs"
```

### 任务 6：迁移后验证

**文件：**
- 仅验证，不修改文件

**步骤 1：检查 diff 格式**

运行：

```bash
git diff --check
```

预期：没有输出。

**步骤 2：检查双语镜像文件集**

运行：

```bash
comm -3 <(cd docs/zh && find . -type f | sort) <(cd docs/en && find . -type f | sort)
```

预期：没有输出。

**步骤 3：最终提交**

```bash
git add docs README.md AGENTS.md tasks
git commit -m "docs: restructure repository for bilingual final outputs"
```
