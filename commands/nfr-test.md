---
description: 独立 NFR 评估（性能/安全/可用性/兼容性）：压测、扫描、故障注入，产出参考报告，不阻塞主流程
argument-hint: "NFR 范围，例如：NF-P-001~003 或 全量（首轮）"
---

<user_input>
$ARGUMENTS
</user_input>

---

委派 **test-manager**（方案/结论）与 **test-engineer**（用例/执行），走独立 NFR 轨。

## 前置

- PRD 已定稿（`docs/prd/prd-nonfunc.md` 存在，含 NF-* 与目标值）。
- 测试版构建可用（`release/artifact/` + build/commit；未完成 → 先执行 `/build-test`）。

## 要求

1. 读取 `rules/team-charter.md`、`docs/prd/prd-nonfunc.md`、测试版构建信息。
2. `test-manager` 用 `skills/nfr-testing` 产出 `test/nfr/plan-nfr.md`（范围/方法/工具/环境/数据/计划）。
3. `test-engineer` 设计 `NFR-CASE`、准备数据、执行并记录 `NFR-RUN`（含 actual 与 evidence）。
4. `test-manager` 产出 `test/nfr/report/NFR-RPT-<NFR-RUN>.md`（指标总表/未达标/风险/建议转缺陷）。

## 边界（硬性）

- **不写 FR 资产**：`test/trace/case-*.json`、`test/data/TD-*`、`test/runs/RUN-*`、`test/bugs/BUG-*` 一律不碰，不进入 `metrics.db`。
- **不阻塞主流程**：NFR 未达标不改变 FR 测试结论与发布判定；核心项未达标须在验收结论列为风险。
- **不直接建 BUG**：未达标项列报告「建议转缺陷」，由 PM 决定是否登记。
- 禁止用开发工作区代替测试版构建做性能/安全评估。
