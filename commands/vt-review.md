---
description: 通用评审入口：PRD 评审 / 设计评审 / 数据模型评审，产出评审报告并驱动闭环
argument-hint: "评审类型与对象，例如：PRD 评审 docs/prd/order 或 设计评审 design/order"
---

<user_input>
$ARGUMENTS
</user_input>

---

> 派发按 charter §5 说明 2b：**经 PM 派发**；评审员无消息通道，问题一律**报 PM 中转**，不得直接发送给责任角色。

按评审类型委派对应评审员 agent，**评审人须包含用户**。

> **评审效力**：AI 评审＝同一模型的自检，不是独立审核（charter §4）；用户确认是唯一人工判断点。

| 评审类型 | 委派角色 | 技能 | 输出 |
|---------|---------|------|------|
| PRD 评审 | prd-reviewer | prd-review | `review/prd/RV-PRD-$COMPONENT-xxx.md` |
| 设计评审 | design-reviewer | design-review | `review/design/RV-DESIGN-$COMPONENT-xxx.md` |
| 数据模型评审 | design-reviewer | datamodel-review | `review/design/RV-DM-$COMPONENT-xxx.md` |

## 要求

1. 读取 `rules/team-charter.md` 与被评审对象。
2. 逐项按对应技能列出的评审角度检查。
3. **按档位产出报告**（charter §9，格式见 `templates/REVIEW-REPORT.md`）：**完整档**按组件分别出报告、PM 汇总；**标准 / 微项目档**合并为**单次全量报告**（一份覆盖全部组件）。每个问题标注**文件 + 模块 + 功能编号**，分级 P0/P1/P2。
4. 给出**总体结论**（通过 / 不通过）。
5. 问题**报告项目经理**，由 PM 派发责任角色修订并中转回评审员验证，跟踪至闭环（评审员无消息通道，不得直接发送）。

## 禁止

- 评审员**除自身评审报告外，只读，不得修改**被评审物。
- 禁止泛泛而谈的结论。

## 档位裁剪（判据与不可裁红线见 charter §9；档位读 `board/KANBAN.md` 首行，未定档按标准档）

- **微项目 / 标准（默认）**：**单次全量报告**覆盖全部组件（见「要求」第 3 条）。
- **完整**：按组件分别出报告，PM 汇总全部组件结论才放行。
