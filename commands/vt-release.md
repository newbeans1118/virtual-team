---
description: 生产版发布：项目验收通过后四方联合确认、构建决策并打 tag
argument-hint: "版本号或范围，例如：v1.0.0"
---

<user_input>
$ARGUMENTS
</user_input>

---

> 派发按 charter §5 说明 2b：**经 PM 派发**；评审员无消息通道，问题一律**报 PM 中转**，不得直接发送给责任角色。

委派 **release-engineer** agent 执行**生产版发布**（阶段二）。

> 测试版构建（阶段一）在代码评审闭环后进行，由 PM 在进入测试阶段前派发，不走本命令。

## 前置（硬性）

- 项目验收评审已通过（`review/project/RV-PROJ-ACCEPT.md`）。

## 要求

1. 读取 `rules/team-charter.md`、`design/`、`test/report/`、验收结论，以及测试版构建阶段产出的 `release/RELEASE-PLAN-DRAFT.md`、`release/ROLLBACK-DRILL.md`、`release/artifact/SHA256SUMS` 与 `sbom.json`。
2. **四方联合确认**：产品经理、测试经理、架构师、代码评审员。
3. **构建决策**：测试期无代码变更 → 测试版构建直接升级标记为生产版；有变更 → 回到 `skills/releasing` 阶段一重新构建（全新 worktree 从主干），并同步重新生成制品校验和、更新发布计划草案与 `ROLLBACK-DRILL.md` 后再确认。
4. **发布计划定稿**：按 `templates/RELEASE-PLAN.md` 把 `release/RELEASE-PLAN-DRAFT.md` 补齐四方确认结论 / 版本号 / tag，定稿为 `release/RELEASE-PLAN-<version>.md`；部署策略 / DB 迁移顺序 / 回滚 / 发布后验证窗口沿用草案，不重新起草。
5. **制品完整性核对**：核对 `SHA256SUMS` 与 `sbom.json` 与本次发布组件一致（缺失或与组件不符 → 重新生成后核对）。
6. **回滚演练核对**：读取 `release/ROLLBACK-DRILL.md`，确认演练在测试环境执行、结果通过且对应本次 build；记录缺失或不匹配不得发布。**不重复演练**（已在测试版构建阶段完成）。
7. **打 tag 并部署**：`git tag` 打在主干 commit 上，按计划执行（含 DB 迁移顺序）。
8. **发布后验证**：≥30 分钟窗口检查错误率 / P95 / 关键业务量（阈值取自 `design/ARCH-NFR.md` §4），超阈值回滚并记录。
9. 发布组件可复现：记录版本、commit、构建命令、依赖版本；产出发布说明交付用户。

## 禁止

- 验收未通过，禁止生产版发布。
- 未经四方联合确认，禁止标记为生产版。
- 禁止在脏工作区直接构建。
- 禁止无发布计划定稿、无 SBOM/校验和、无有效 `ROLLBACK-DRILL.md` 就发布生产版。
- 禁止跳过发布后验证窗口。
