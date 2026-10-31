---
description: 立项并产出立项报告（docs/PROJ_$PROJECT_NAME.md）
argument-hint: "项目名称与简述，例如：order-center 在线订单管理系统"
---

<user_input>
$ARGUMENTS
</user_input>

---

委派 **project-manager** agent 执行**立项**。

## 要求

1. 先读取 `rules/team-charter.md`。
2. 使用 `planning` 技能。
3. 与用户澄清以下要素（不确定必须提问）：
   - 项目名 `$PROJECT_NAME`、一句话定位、目标用户、核心业务
   - 范围（含明确的不做项）
   - 技术栈、用户规模、性能/安全约束、交付形态
4. 产出 `docs/PROJ_$PROJECT_NAME.md`，结构严格遵循 `templates/PROJECT.md`。
5. 完成后提交**立项评审**（用户 + project-reviewer）。

## 禁止

- 禁止跳过用户确认直接产出立项报告。
- 禁止猜测缺失信息。
