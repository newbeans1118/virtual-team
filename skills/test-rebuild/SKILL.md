---
name: test-rebuild
description: 从执行记录派生覆盖率矩阵与度量报告、执行一致性校验时使用。触发场景：测试执行完成后需要统计成功率/修复率/重开率/覆盖率、需要生成覆盖率矩阵、需要检测孤立用例/未覆盖功能点/源不同步、需要按模块或数据集切片分析、提到度量报告、测试统计、覆盖率计算、追溯矩阵。
---

# 测试追溯重建与度量（test-rebuild）

## 目的

从**不可变的原始记录**（PRD/CASE/PLAN/EXEC/BUG 五方）**派生**出人可读的矩阵与度量——原始记录只追加不改写，指标永远可复算。

## 执行者

`test-engineer`（执行后跑）；结果供 `test-manager` 评估判定

## 输入（五方数据，全部已存在；**分片 aware**——多实例并行产出，本技能全量消费）

| 方 | 来源 | 角色 |
|----|------|------|
| 需求 | `docs/prd/$COMPONENT/$MODULE/trace/prd.json`（分片） | 功能点全集 + **acceptance 验证条件条列**（测试点级分母） |
| 用例 | `test/trace/$COMPONENT/$MODULE/case.json`（分片） | 覆盖关系（function_refs / **acceptance_refs** / dataset_refs） |
| 数据 | `test/trace/$COMPONENT/$MODULE/TD-REGISTRY.json`（**分片**，合并读取；SQLite 轨=td_registry 表） | 数据单元（黑盒：id + description + load_entry） |
| 执行 | `test/runs/RUN-xxx.json`（**计划态，TM 建**）+ `RUN-xxx/EXEC-PLAN.json` + `EXEC.jsonl`（**按组件/模块分片**） | 计划配对 + 执行明细（**轮次汇总唯一来源**） |
| 缺陷 | `test/bugs/BUG-xxx.json` | 缺陷状态机 |

## 输出（全部**派生只读**，禁止手工编辑）

- `test/trace/coverage-matrix.md`——需求×用例×执行 覆盖率矩阵
- `test/trace/index.json`——轻量索引（模块清单/统计摘要，供检索）
- `test/report/test-metrics-$RUN.md`——本轮度量报告（模板 `templates/TEST-METRICS.md`）
- 校验结论（写在各派生文件头部）

## 存储选择（开工第一步）

读 `rules/storage-track.md`（唯一规则源）+ `test/STORE-CONFIG.json`，**只加载所选轨道一节的规则**：`store=json` → 读五方文件全量计算；`store=sqlite` → SQL 聚合查询（八项指标现成 SQL 见 `templates/SQLITE-SCHEMA.sql` 尾部）。输出物两轨相同。配置缺失 → BLOCKED 报 PM。

## 一致性校验（每次必跑，四项）

| # | 校验 | 规则 | 违规处理 |
|---|------|------|---------|
| 1 | **ID 完整性** | 每个 `function_refs` 必须存在于 PRD 分片；每条 EXEC 的 case/td 必须存在于 CASE/REGISTRY | 孤立项 = P0，报告 PM |
| 2 | **覆盖完整性** | 每个功能点 ≥1 条 active 用例；每条 active 用例 ≥1 个 TD | 缺口显式列出（**禁止标"通过"**） |
| 3 | **源同步** | `prd.md` hash == `prd.json.source_hash`；`prd.json` hash == `case.json.prd_source_hash` | 不同步 = 提示对应技能重跑，指标标 `stale` |
| 4 | **状态合法** | 枚举校验；BUG 状态机合法迁移；TD 的 owner_cases 与用例侧 `dataset_refs` 双向一致 | 违规 = P1 |
| 5 | **验证条件引用完整性** | 每个 `acceptance_refs` 项必须存在于对应功能点的 `acceptance[].key`；引用闭合（前缀 fr-id ∈ 本用例 function_refs） | 悬空引用 = **告警**（列「遗留风险」，不阻塞） |

## 度量指标（公式 + 出处）

| 指标 | 公式 | 出处 |
|------|------|------|
| **轮次汇总** | 按 RUN 聚合 EXEC：`{total, pass, fail, blocked}`（**RUN 头不承载 summary——本表为唯一汇总口径**） | EXEC.run_id |
| 需求覆盖率 | 有 ≥1 active 用例的功能点 ÷ 全部 active 功能点 | prd × case |
| **测试点级覆盖率**（度量，非门禁） | 被 ≥1 active 用例 `acceptance_refs` 引用的验证条件数 ÷ 全部 active 功能点的 acceptance 条件总数 | prd.acceptance × case.acceptance_refs |
| **路径覆盖度**（度量，按 kind 分组） | 各 kind（normal/boundary/negative）已覆盖条件数 ÷ 该 kind 条件总数 | prd.acceptance.kind |
| 用例执行率 | 已执行 PLAN 行 ÷ 计划 PLAN 行 | PLAN vs EXEC |
| 通过率 | pass EXEC ÷ 已执行 EXEC（**按轮**；可按组件/模块/优先级/suitable_for 切片） | EXEC.jsonl 分片 |
| 缺陷密度 | bug 数 ÷ 执行数（或 ÷ 功能点数） | EXEC × BUG |
| 修复率 | verify_pass 的 bug ÷ 提交修复的 bug | BUG.verification |
| 重开率 | reopen 次数 ÷ closed bug 数（**质量逃逸信号**） | BUG 状态历史 |
| 回归通过率 | trigger=regression 轮的 pass ÷ executed | RUN.trigger 过滤 |
| 自动化率 | automatable 用例 ÷ 全部用例 | CASE.automation |

> **测试点级覆盖率与路径覆盖度仅作度量**——写入报告供 test-manager 诊断；**是否阻塞由 test-manager 判断，不自动门禁**。缺口报告列出未覆盖的 `{fr-id}:{key}` 及其 kind。

> 度量**只汇总不创造**：任何数字必须能从原始记录复算；公式与出处写在报告内。

## 流程

1. 校验五方数据存在性与合法性（缺任一方 → BLOCKED，报告缺口）。
2. 跑五项一致性校验，记录结论。
3. 生成 `coverage-matrix.md`（功能点 → **验证条件** → 用例 → 数据 → 最近执行结果 → 关联缺陷）。
4. 生成 `index.json`（模块/用例/TD 摘要统计）。
5. 生成 `test-metrics-$RUN.md`（指标表 + **测试点级覆盖率与路径覆盖度** + 缺口清单 + 切片分析 + 遗留风险）。
6. 交 `test-manager` 评估（准出判定用）。

## 质量要求

- **可复算**：同一批五方原始数据重跑，指标必须一致；不一致说明算法有隐藏状态。
- **不隐藏缺口**：未覆盖的验证条件、无 TD 的用例、`stale` 源全部列出，不得只报好看的数字。
- **派生只读**：所有输出文件由本技能生成，禁止手工编辑（下次 rebuild 覆盖）。

## 检查清单

- [ ] 五方数据齐全且合法（缺任一 → BLOCKED 并报告缺口）
- [ ] 五项一致性校验已跑，结论已记录（含 `stale` 判定）
- [ ] `coverage-matrix.md` 覆盖到**验证条件级**（不止功能点）
- [ ] `index.json` 与 `test-metrics-$RUN.md` 已产出
- [ ] 轮次汇总按 RUN 聚合 EXEC（**不从 RUN 头读 summary**——RUN 头不承载）
- [ ] 缺口清单完整（未覆盖条件 / 无 TD 用例 / stale 源）
- [ ] 指标公式与出处一致（按本技能「度量指标」表）
- [ ] 未手工编辑任何派生文件

## 触发与边界

**该用**：每轮执行结束后；缺陷回归关闭后；交付评估前。

**不该用**：
- 修改任何原始记录（五方数据对它是只读的）
- 判定"测试是否通过" → `test-manager`
- 生成执行实例 → `case-instantiate`
- 人工可读的轮次总结报告 → `case-running` 的 RPT（本技能出**度量**，不出交付叙事）

## 常见错误

- 手工编辑派生文件（下次 rebuild 会被覆盖——原始记录才是真相）。
- 覆盖率只算"有用例"不算"有数据"（无 TD 的用例无法执行，是假覆盖）。
- **覆盖率只算到功能点级**，不展开 acceptance 条件（漏掉功能点内部未覆盖的条件；应输出测试点级覆盖率与缺口）。
- 忽略 `stale` 标记继续出报告（需求已变，指标失真）。
- 修复率分母用错（应为"已提交修复的 bug"，不是全部 bug）。
