---
description: 设计阶段：产出架构、数据库、功能/接口/算法/日志设计并搭建工程
argument-hint: "设计范围，例如：全部组件 或 workbench 组件"
---

<user_input>
$ARGUMENTS
</user_input>

---

> 派发按 charter §5 说明 2b：**经 PM 派发**；评审员无消息通道，问题一律**报 PM 中转**，不得直接发送给责任角色。

委派 **architect** agent 执行**架构设计**。

## 前置

- PRD 评审已通过（`docs/prd/` 完备）。

## 要求

1. 读取 `rules/team-charter.md`、`docs/prd/`。
2. 依次使用技能：
   - `architecting` → `design/ARCH.md`（组件索引+追溯矩阵，开发者必读）+ `design/ARCH-NFR.md`（容量/威胁/可观测）
   - `data-modelling` → 全局 `design/DATABASE.md`（组件数据索引+全局规范+跨组件引用）+ 每组件 `design/$COMPONENT/database.md`（表结构/索引/DDL/迁移）
   - `general-design` → 全局 `design/INTERFACE.md`（横切契约 + 组件接口索引）、`design/LOGGER.md`（日志规范）；按组件 `design/$COMPONENT/interface.md` 与 `design/$COMPONENT/func.md`（组件 FR > 12 或 func.md > 300 行时按模块拆 `$MODULE/func.md`）
   - `diagramming` → 架构图/ER 图/时序图（Mermaid）
3. **搭建工程目录与构建系统并验证**（实际执行构建命令）。
4. 校验：每条 FR 在设计中有落点；组件 interface/func 齐全；DDL 与数据字典一致；FUNC 拆分阈值合规。
5. 完成后**按组件提交设计评审第一轮**（用户 + design-reviewer，报告 `RV-DESIGN-$COMPONENT-xxx.md`），数据层可加做 `datamodel-review`（`RV-DM-$COMPONENT-xxx.md`）；PM 汇总全部组件结论。
6. 第一轮通过并完成设计修订定稿后，**由 PM 派发 architect** 用 `task-breakdown` 产出 `design/DEV-TASKS.md`，提交**设计评审第二轮（分解评审）**——同一 design-reviewer、同一门禁、同一批报告；PM 汇总两轮均通过才放行进入 `/vt-coding`（charter §5）。本命令不产出 DEV-TASKS。
