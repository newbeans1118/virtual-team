---
description: 项目验收：交付前对项目做总体评估，确认功能与质量是否达标
argument-hint: "验收范围，例如：v1.0.0 全量验收"
---

<user_input>
$ARGUMENTS
</user_input>

---

委派 **project-reviewer** agent 执行**项目验收**（评审人含**用户**）。

## 要求

1. 读取 `rules/team-charter.md`、`docs/`、`design/`、`review/`、`test/report/`、`release/`。
2. 用 `accepting` 技能评估：
   - 目标达成度（biz-xxx / fr-xxx 实现与验收回溯）
   - 各阶段评审是否闭环
   - P0/P1 是否清零
   - 非功能指标是否达标
   - 发布物是否符合生产版条件
3. 产出 `review/project/RV-PROJ-ACCEPT.md`，给出**通过 / 不通过**结论。
4. 结论须标注是否已获用户确认。
