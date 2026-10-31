---
description: 设计阶段：产出架构、数据库、功能/接口/算法/日志设计并搭建工程
argument-hint: "设计范围，例如：全部组件 或 workbench 组件"
---

<user_input>
$ARGUMENTS
</user_input>

---

委派 **architect** agent 执行**架构设计**。

## 前置

- PRD 评审已通过（`docs/prd/` 完备）。

## 要求

1. 读取 `rules/team-charter.md`、`docs/prd/`。
2. 依次使用技能：
   - `architecting` → `design/ARCH.md`（含组件索引与追溯矩阵）
   - `data-modelling` → `design/DATABASE.md`（组件/模块索引 + 按组件/模块分节）
   - `general-design` → 全局 `design/INTERFACE.md`（横切契约 + 组件接口索引）、`design/LOGGER.md`（日志规范）；按组件 `design/$COMPONENT/interface.md` 与 `design/$COMPONENT/func.md`（组件 FR > 12 或 func.md > 300 行时按模块拆 `$MODULE/func.md`）
   - `diagramming` → 架构图/ER 图/时序图（Mermaid）
3. **搭建工程目录与构建系统并验证**（实际执行构建命令）。
4. 校验：每条 FR 在设计中有落点；组件 interface/func 齐全；DDL 与数据字典一致；FUNC 拆分阈值合规。
5. 完成后**按组件提交设计评审**（用户 + design-reviewer，报告 `RV-DESIGN-$COMPONENT-xxx.md`），数据层可加做 `datamodel-review`（`RV-DM-$COMPONENT-xxx.md`）；PM 汇总全部组件结论。
