---
description: 通用评审入口：PRD 评审 / 设计评审 / 数据模型评审，产出评审报告并驱动闭环
argument-hint: "评审类型与对象，例如：PRD 评审 docs/prd/order 或 设计评审 design/order"
---

<user_input>
$ARGUMENTS
</user_input>

---

按评审类型委派对应评审员 agent，**评审人须包含用户**。

| 评审类型 | 委派角色 | 技能 | 输出 |
|---------|---------|------|------|
| PRD 评审 | prd-reviewer | prd-review | `review/prd/RV-PRD-$COMPONENT-xxx.md` |
| 设计评审 | design-reviewer | design-review | `review/design/RV-DESIGN-$COMPONENT-xxx.md` |
| 数据模型评审 | design-reviewer | datamodel-review | `review/design/RV-DM-$COMPONENT-xxx.md` |

## 要求

1. 读取 `rules/team-charter.md` 与被评审对象。
2. 逐项按对应技能列出的评审角度检查。
3. **按组件**产出报告（格式见 `templates/REVIEW-REPORT.md`），每个问题标注**文件 + 模块 + 功能编号**，分级 P0/P1/P2；PM 汇总全部组件结论。
4. 给出**总体结论**（通过 / 不通过）。
5. 发送问题给责任角色，跟踪至闭环。

## 禁止

- 评审员**除自身评审报告外，只读，不得修改**被评审物。
- 禁止泛泛而谈的结论。
