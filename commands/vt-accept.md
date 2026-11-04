---
description: 项目验收：交付前对项目做总体评估，确认功能与质量是否达标
argument-hint: "验收范围，例如：v1.0.0 全量验收"
---

<user_input>
$ARGUMENTS
</user_input>

---

> 派发按 charter §5 说明 2b：**经 PM 派发**；评审员无消息通道，问题一律**报 PM 中转**，不得直接发送给责任角色。

委派 **project-reviewer** agent 执行**项目验收**（评审人含**用户**）。

## 要求

1. 读取 `rules/team-charter.md`、`docs/`、`design/`、`review/`、`test/report/`，以及 `release/` 下**测试版构建阶段**产物（发布计划草案 / 制品校验文件 / 回滚演练记录 / 手册）。
2. 用 `accepting` 技能评估：
   - 目标达成度（biz-xxx / fr-xxx 实现与验收回溯）
   - 各阶段评审是否闭环
   - P0/P1 是否清零
   - 非功能设计落地与 NFR 报告（**仅参考，不阻塞判定**）
   - 发布物候选完整性（草案 / SHA256SUMS / SBOM / 回滚演练记录）
3. 产出 `review/project/RV-PROJ-ACCEPT.md`，给出**通过 / 不通过**结论。
4. 结论须标注是否已获用户确认。

> **时序**：验收在 `/vt-release` **之前**，只读取测试版构建阶段已落盘的证据。生产版 `RELEASE-PLAN-<version>.md`、四方联合确认结论、tag、发布后验证均属发布阶段产物，**不得作为验收前置**。
