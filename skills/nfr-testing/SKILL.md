---
name: nfr-testing
description: 独立评估非功能需求（性能/安全/可用性/兼容性）时使用。触发场景：需要压测、安全扫描、故障注入、兼容矩阵、产出 NFR 报告、提到 NFR 测试、非功能测试、性能测试、安全测试、压测。与 FR 用例流程完全独立，结果仅作参考，不阻塞发布。
---

# NFR 独立评估（nfr-testing）

## 目的

对 `prd-nonfunc.md` 的 NF-* 需求做独立评估：设计 NFR 用例、执行测量、产出**参考报告**。

**与 FR 测试的关系**：平行轨，互不阻塞、互不干扰——不共用用例/数据/RUN/EXEC/度量，不改变 FR 结论与发布判定。

## 执行者

`test-manager`（方案与结论）/ `test-engineer`（用例与执行）

## 输入

- `docs/prd/prd-nonfunc.md`（NF-P / NF-S / NF-A 清单与目标）
- **`design/ARCH-NFR.md`**：§2 容量与负载基线（`load_model` 须与架构估算一致，不得拍脑袋）、§3 威胁清单（渗透/扫描用例来源）、§4 SLI/SLO（指标口径与目标值来源）
- 测试版构建产物（`/vt-build-test`：artifact + build/commit）
- 环境规格与可用工具

## 输出（全部落 `test/nfr/`）

- `test/nfr/plan-nfr.md`（NFR 方案，模版 `templates/NFR-PLAN.md`）
- `test/nfr/cases/NFR-CASE-$COMPONENT-NNN.md` + `test/nfr/trace/nfr-case-$MODULE.json`（模版 `templates/NFR-CASE.json`）
- `test/nfr/data/NFR-TD-$COMPONENT-NNN/`（可选；沿用 TD 六字段结构，但 **`owner_cases` 指向 `NFR-CASE-*` 而非 FR CASE**，`suitable_for` 可留空——NFR 不按 kind 配对；也可 `reuse:TD-*` 只读复用 FR 数据）
- `test/nfr/runs/NFR-RUN-NNN.json`（模版 `templates/NFR-RUN.json`）
- `test/nfr/report/NFR-RPT-<NFR-RUN>.md`（模版 `templates/NFR-REPORT.md`）

## 流程（五步，顺序固定）

### 1. 选范围

从 `prd-nonfunc.md` 取 NF-*，按「核心 / 一般」排序；标注本轮纳入与不纳入（不纳入须写理由，如环境不具备）。

### 2. 出方案

按 `templates/NFR-PLAN.md` 写 `test/nfr/plan-nfr.md`：方法/工具/负载模型/环境/数据策略/执行计划。

### 3. 设计 NFR 用例

- 每个用例声明 `nf_refs`（可多条）、`method`、`load_model`、`metrics`（name/target/unit/op）、`evidence_format`
- 指标必须**可判定**：目标值 + 比较符 + 单位；无目标的 NFR 不得进入执行
- 数据：新建 `NFR-TD-*` 或 `reuse:TD-*`（只读，不改 FR 数据单元）

### 4. 执行并记录

- 用方案指定的工具执行，原始报告落 `test/nfr/runs/NFR-RUN-NNN/`
- 每个 item 记录 `metric.actual` 与 `passed`（按 op 比较 target）
- 缺实测值 → `passed=false` 且注明原因，**不得留空当通过**

### 5. 出报告

按 `templates/NFR-REPORT.md` 产出 `NFR-RPT-*`：指标总表 / 未达标与风险 / 建议转缺陷 / 结论。

## 隔离红线（硬性）

- **不写** FR 的 `test/trace/case-*.json`、`test/data/TD-*`、`test/runs/RUN-*`、`test/bugs/BUG-*`
- **不进** `metrics.db`（NFR 轨仅 JSON，量小无需双轨）
- **不直接建 BUG**：未达标项写入报告「建议转缺陷」，由 PM 决定是否登记
- **不影响** FR 通过率、FR 覆盖缺口、发布判定
- 可复用 FR 的 TD（只读）与测试版构建，但不得改动它们

## 质量要求

- 每条**纳入本轮**的 NF-* 至少被一个 `NFR-CASE` 覆盖（不纳入须在方案写明理由）
- 指标可判定：`target` + `op` + `unit` 齐全；实测值有原始证据
- 环境与生产差异显式声明（否则性能结论不可迁移）
- 报告数字与 `NFR-RUN` 一致，不手填

## 检查清单

- [ ] `plan-nfr.md` 已产出（范围/方法/环境/数据/计划）
- [ ] 每条纳入的 NF-* 有 NFR-CASE 且 `nf_refs` 指向存在
- [ ] `metrics` 的 target/op/unit 齐全
- [ ] NFR-RUN 记录了 build/commit、env、actual、evidence
- [ ] 报告含未达标项、风险与「建议转缺陷」
- [ ] 未写入 FR 资产、未建 BUG、未改 metrics.db

## 触发与边界

**该用**：需要性能/安全/可用性/兼容性评估；发布前想要一份 NFR 参考结论。

**不该用**：
- FR 功能用例设计与执行 → `case-design` / `case-instantiate` / `case-running`
- FR 缺陷登记与回归 → `case-running`（NFR 只提建议）
- 度量统计 FR 覆盖率 → `test-rebuild`

## 常见错误

- 把 NFR 用例塞进 FR 的 `case-*.json`（两轨混写，互相污染）
- 指标只写"响应快/安全"（不可判定）
- 性能测试用开发工作区而非测试版构建（结论不可迁移）
- 未达标直接开工单（越界；应由 PM 决定）
- 报告手抄数字（与 NFR-RUN 脱节）
