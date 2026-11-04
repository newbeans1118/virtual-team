---
description: 更新并展示项目进度看板（board/KANBAN.md）
argument-hint: "无需参数，直接查看/刷新看板"
---

<user_input>
$ARGUMENTS
</user_input>

---

> 派发按 charter §5 说明 2b：**经 PM 派发**；评审员无消息通道，问题一律**报 PM 中转**，不得直接发送给责任角色。

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

## 档位裁剪（判据与不可裁红线见 charter §9；档位读 `board/KANBAN.md` 首行，未定档按标准档）

- **微项目**：甘特图可免，看板用列表即可。
- **标准（默认）**：任务数 > 20 时出甘特图。**完整**：必出甘特图。
- 任何档位都保留「看板单一写者 = PM」。
