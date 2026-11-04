---
description: 立项并产出立项报告（docs/PROJ_$PROJECT_NAME.md）
argument-hint: "项目名称与简述，例如：order-center 在线订单管理系统"
---

<user_input>
$ARGUMENTS
</user_input>

---

> 派发按 charter §5 说明 2b：**经 PM 派发**；评审员无消息通道，问题一律**报 PM 中转**，不得直接发送给责任角色。

委派 **project-manager** agent 执行**立项**。

## 要求

1. 先读取 `rules/team-charter.md`。
2. 使用 `planning` 技能。
3. 与用户澄清以下要素（不确定必须提问）：
   - 项目名 `$PROJECT_NAME`、一句话定位、目标用户、核心业务
   - 范围（含明确的不做项）
   - 技术栈、用户规模、性能/安全约束、交付形态
4. 产出 `docs/PROJ_$PROJECT_NAME.md`，结构严格遵循 `templates/PROJECT.md`。
5. 完成后**提交立项评审**：由 PM 派发 `project-reviewer` 用 `accepting` 技能评审（评审人含用户），产出 `review/project/RV-PROJ-KICKOFF.md` 并给出明确**通过 / 不通过**结论；未通过则修订后重审。该结论是 `/vt-prd` 的硬性前置。

## 禁止

- 禁止跳过用户确认直接产出立项报告。
- 禁止猜测缺失信息。
