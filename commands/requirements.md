---
description: 需求分析阶段：产出业务分析、规格说明书、数据字典与原型
argument-hint: "模块名或范围，例如：user-auth 用户认证模块"
---

<user_input>
$ARGUMENTS
</user_input>

---

委派 **product-manager** agent 执行**需求分析**。

## 前置

- 必须已存在 `docs/PROJ_$PROJECT_NAME.md`（否则先执行 `/kickoff`）。

## 要求

1. 读取 `rules/team-charter.md` 与立项报告。
2. 依次使用技能：
   - `business-analysis` → `docs/requirements/overview.md`、`biz-$MOD.md`
   - `requirement` → `spec-$MOD.md`、`spec-nonfunc.md`、`dict.md`
   - `prototype` → `pages/prototype/`
   - `req-structure` → `docs/requirements/trace/req-$MOD.json`
   - `diagramming` → 业务流程图（Mermaid）
3. 所有输出遵循 `templates/` 对应模版。
4. 校验：所有 `biz-xxx` 被 `fr-$MOD-xxx` 覆盖（附追溯矩阵）。
5. 完成后提交**需求评审**（用户 + requirement-reviewer）。

## 禁止

- 禁止创建无法独立验收的"功能点"。
- 禁止跳过与用户确认业务规则。
