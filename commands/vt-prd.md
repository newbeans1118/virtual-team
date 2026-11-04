---
description: 需求分析阶段：产出业务分析、PRD、数据字典与原型（/vt-prd）
argument-hint: "组件/模块名或范围，例如：workbench 工作台组件"
---

<user_input>
$ARGUMENTS
</user_input>

---

> 派发按 charter §5 说明 2b：**经 PM 派发**；评审员无消息通道，问题一律**报 PM 中转**，不得直接发送给责任角色。

委派 **product-manager** agent 执行**需求分析**。

## 前置

- 必须已存在 `docs/PROJ_$PROJECT_NAME.md`（否则先执行 `/vt-kickoff`）。
- **立项评审结论为通过**（`review/project/RV-PROJ-KICKOFF.md`）；未产出或结论非通过 → BLOCKED 报 PM，不得进入需求分析。

## 要求

1. 读取 `rules/team-charter.md`、`rules/decision-brief.md` 与立项报告。
2. 依次使用技能：
   - `business-analysis` → `docs/prd/overview.md`、各组件/模块 `ba.md`
   - `prd` → 各组件/模块 `prd.md`、`prd-nonfunc.md`、`dict.md`
   - `prototype` → `pages/prototype/$COMPONENT/`
   - `prd-structure` → `docs/prd/$COMPONENT/$MODULE/trace/prd.json`
   - `diagramming` → 业务流程图（Mermaid）
3. 所有输出遵循 `templates/` 对应模版。**RTM 不手写**：`prd-structure` 与原型完成后跑 `python scripts/gen_docs.py --root . --type rtm`，§4 覆盖校验须为「通过」（不通过回源补 `biz_refs`/`acceptance`，不改 RTM）。
4. 校验：所有 `biz` 被 `fr` 覆盖（附追溯矩阵）；`ba.md` §8 待确认台账**未处理完不得进入 `prd`**（有假设 + 有责任人 + 有回填点者可放行，同 gated 标准）。
5. 完成后**按档位提交 PRD 评审**（charter §9，评审人须含用户）：完整档按组件出 `RV-PRD-$COMPONENT-xxx.md` 并由 PM 汇总；标准 / 微项目档出**单次全量报告** `review/prd/RV-PRD-ALL-xxx.md`。

## 两个强制确认门（业务分析阶段，必停）

不得一步到位。以下两处**必须停下等用户答复**，并在报告留痕「经用户确认：X」：

- **G1 主干确认**：业务主干流程（角色 → 环节 → 交接）出来后即停，用户确认前**不得往下挖规则**。
- **G2 规则确认**：决策表（判断点 → 条件组合 → 结果）出来后即停，用户确认前**不得出 PRD**。

用户未答复 → 转 `NEEDS_CONTEXT` 报项目经理，**不得自行猜答案继续**。

## 关于材料

优先向用户索取**原始材料**（访谈转写、会议纪要原文、截图、规则表、旧 PRD 草稿），不要让用户"先消化再给"。必问项只有 4 个：业务目标、角色与职责边界、触发条件、异常兜底责任归属；其余取默认值并标 `[假设]`。

## 禁止

- 禁止创建无法独立验收的"功能点"。
- 禁止跳过与用户确认业务规则。
- 禁止用行业惯例填充未知规则——一律标 `[TBD: 待确认]` 并进台账。
- 禁止只画 happy path（每个菱形必须有否分支）。

## 档位裁剪（判据与不可裁红线见 charter §9；档位读 `board/KANBAN.md` 首行，未定档按标准档）

- **微项目**：界面原型可免（写理由）；PRD 评审出**单次全量报告**。
- **标准（默认）**：原型按需；PRD 评审单次全量报告。
- **完整**：必出原型；按组件出评审报告并由 PM 汇总。
