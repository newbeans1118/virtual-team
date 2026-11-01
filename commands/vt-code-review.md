---
description: 代码评审：评审代码完整性/正确性/质量/安全/性能并驱动修复闭环
argument-hint: "评审范围，例如：src/workbench 组件"
---

<user_input>
$ARGUMENTS
</user_input>

---

委派 **code-reviewer** agent 执行**代码评审**（两阶段，顺序不可颠倒）。

> **缺陷修复评审**：P0/P1 修复后以 BUG 编号 + fix commit 为输入，走**单阶段修复评审**（五项检查，见技能同名小节），结论回填 `BUG.fix.review`。

## 要求

1. 读取 `rules/team-charter.md`、`rules/engineering-discipline.md`、`docs/prd/`、`design/`、`src/`。
2. 使用 `code-review` 技能，**先做阶段一规格符合性**（功能编号是否全实现、有无多做/漏做），**再做阶段二代码质量**（正确性/质量/安全/性能/可维护）。
3. 产出报告 `review/code/CR-CODE-xxx.md`，每个问题须标注**文件 + 模块 + 功能编号**，并分级 P0/P1/P2；给出两阶段各自的结论。
4. 发送问题给责任工程师；工程师修复后回复；评审员验证并关闭，形成闭环。

## 禁止

- **除自身评审报告外，只读代码不得修改**（必要时可运行验证，但不得改动被评审物）。
- 禁止跳过规格符合性、只评代码质量。
- 禁止只报告不跟踪。
