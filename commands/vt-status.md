---
description: 更新并展示项目进度看板（board/KANBAN.md）
argument-hint: "无需参数，直接查看/刷新看板"
---

<user_input>
$ARGUMENTS
</user_input>

---

委派 **project-manager** agent 更新并展示进度看板。

## 要求

1. 读取 `rules/team-charter.md`、`board/KANBAN.md`、各阶段评审报告。
2. 刷新 `board/KANBAN.md`：
   - 任务状态（待办/进行中/待评审/已通过/打回）
   - 阶段门禁状态
   - 里程碑甘特图（Mermaid）
   - 缺陷/风险摘要
3. 以**适合人查看**的表格 + Mermaid 呈现给用户，指出当前阻塞项与下一步动作。

## 禁止

- 禁止只写内部代号；呈现必须让人一眼看懂。
