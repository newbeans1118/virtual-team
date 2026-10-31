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

- 需求评审已通过（`docs/requirements/` 完备）。

## 要求

1. 读取 `rules/team-charter.md`、`docs/requirements/`。
2. 依次使用技能：
   - `architecting` → `design/ARCH.md`
   - `data-modelling` → `design/DATABASE.md`
   - `general-design` → `design/FUNC.md`、`DATASTRUCT-ALGORITHM.md`、`INTERFACE.md`、`LOGGER.md`
   - `diagramming` → 架构图/ER 图/时序图（Mermaid）
3. **搭建工程目录与构建系统并验证**（实际执行构建命令）。
4. 校验：设计条目与功能编号可追溯；DDL 与数据字典一致。
5. 完成后提交**设计评审**（用户 + design-reviewer），数据层可加做 `datamodel-review`。
