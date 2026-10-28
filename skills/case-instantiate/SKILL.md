---
name: case-instantiate
description: 建立执行轮（RUN）、把用例与数据单元配对生成可执行实例（执行实例计划）时使用。触发场景：需要按轮次组织测试、建 RUN 并声明环境池、把静态用例与 TD 数据配对成可执行实例、产出 EXEC-PLAN-模块.json 并交 test-manager 审定、提到生成执行计划、实例化、用例数据配对、执行轮准备。
---

# 测试实例化（case-instantiate）

## 目的

**实例化（instantiate）**：把**静态资产**（用例 + 数据单元）转成**可执行实例**。

- 一个 `用例 × 数据` = 一个**可执行实例**（EXEC-PLAN 行）；`expected` 是实例的属性。
- 本技能只做**准备**：建 RUN → 配对生成实例 → 交审定。**不执行**（执行属 `case-running`）。

> 与 `case-running` 的分工：**本技能产出实例计划（设计型产物，需审定）**；`case-running` 消费它并产出执行明细（运行型产物，追加式）。

## 执行者

`test-engineer`（实例计划由 `test-manager` 审定）

## 输入

- `test/plan.md`（测试方案，含范围与环境要求）
- 本模块 `test/trace/case-$MOD.json`（用例分片，含 `function_refs`/`acceptance_refs`/`dataset_refs`）
- 本模块注册表分片 `test/data/trace/TD-REGISTRY-$MOD.json`（SQLite 轨：查库）
- `docs/requirements/trace/req-$MOD.json`（acceptance 文本，expected 来源之一）

## 输出（按存储轨道 × 分片）

**分片规则**：实例计划**按模块分片**——一个 test-engineer 实例只负责一个 `$MOD`，只产出本模块实例计划分片；多实例并行零交叉。

- **JSON 轨**（默认）：
  - `test/runs/RUN-xxx.json`（**RUN 头**：id / trigger / scope / `envs` 池 / started_at；**summary 留空**，由 `case-running` 汇总）
  - `test/runs/RUN-xxx/EXEC-PLAN-$MOD.json`（本模块实例计划，**TM 审定后生效**）
- **SQLite 轨**（STORE-CONFIG.store=sqlite）：写 `test/trace/metrics.db`
  - `runs` 行（INSERT RUN 头；`envs` 列为 JSON 数组）
  - `exec_plans` 行（plan_id / module / run_id / case_id / td_id / expected / source / approved=0）
  - `approved` 列承载 TM 审定标记（未审定行禁止执行）

## 存储选择（开工第一步）

读 `test/STORE-CONFIG.json`——**项目立项时已一次性选定，全程跟随；仅允许一次 json→sqlite 单向迁移**（迁移后不可逆）。
- `store=json` → 写文件（RUN 头 + EXEC-PLAN-$MOD.json）。
- `store=sqlite` → 入库（`runs` + `exec_plans`）。
- 配置缺失 → **BLOCKED 报项目经理**（立项时未完成存储决策，不得代为默认选轨）。**数据契约（实体/字段/关联）两轨完全一致，仅读写方式不同。**

## 执行轮类型（trigger）

| 类型 | 范围 | 触发时机 |
|------|------|---------|
| `full` | 全部 active 用例 | 首轮 / 交付前 |
| `regression` | 修复相关 + 核心路径 | 缺陷修复后 / 里程碑 |
| `smoke` | 核心冒烟集 | 每次部署后 |
| `defect-verify` | 指定 BUG 的验证用例 | 修复完成后（`defect_refs` 必填） |

## 流程（三步，顺序固定）

### 1. 建 RUN

按 trigger 确定 scope，写 **RUN 头**：`{id, trigger, defect_refs, scope, envs, started_at}`。
- **声明 `envs` 数组**（本轮可用的被测环境池，每项含 name/build/commit——**证据**）。
- **`summary` 留空**（由 `case-running` 在执行完成后汇总填充）。
- RUN 是度量的分母单位；**envs 是执行期独占租用的资源池**（同时活跃分片数 ≤ envs 数）。

### 2. 配对生成实例（按模块分片）

- 从 RUN 范围内**本模块**的 active 用例出发，按本模块 TD 注册表分片 `suitable_for` 匹配"用例 × 数据"。
- 参考用例侧 `dataset_refs`（该用例声明的可用数据单元）与 TD 侧 `owner_cases`（双向一致），确定配对。
- 每个配对生成一行 `{plan_id, case, td, expected, source}`：
  - **`expected`** 是实例属性——从用例预期语义 / TD 单元内部 `expected_hints` / 需求 `acceptance` 文本提炼，或项目补充；**同一 TD 配不同用例预期不同**。
  - **`source`** 取值：`case-expected | expected-hints | acceptance | manual`。
  - **`plan_id`（P-xxx）在 RUN 内全局唯一**（跨模块分片不重号）——EXEC 的 `plan_ref` 据此回指。
- 产出**本模块实例计划分片** `EXEC-PLAN-$MOD.json`。

### 3. 提交审定

- 交 `test-manager` **审定**：配对合理性（case × td）、expected 完整性、plan_id 唯一性。
- **按模块分片独立放行**（不要求等齐全部模块——避免同步屏障；跨片由审定时的全局查重保障）。
- **未经审定不得进入执行**（`case-running` 的前置硬门禁）。

## 质量要求

- 每个 active 用例的每个 `dataset_refs` 应至少形成一个实例（覆盖其数据维度）；未形成须说明理由。
- `plan_id` RUN 内唯一；`expected` 非空且可判定。
- 配对必须与 TD 的 `suitable_for` 语义一致（边界数据不能配 normal 型用例）。
- **不越界**：本技能不执行、不记录结果（属 `case-running`）。
- 分片只写本模块产物，不改其他实例分片。

## 检查清单

- [ ] RUN 头已建立（含 `envs` 池与 build/commit 证据；summary 留空）
- [ ] 本模块实例计划分片已生成
- [ ] 每行含 plan_id/case/td/expected/source，plan_id 全局唯一
- [ ] expected 非空、可判定、来源标注正确
- [ ] 配对与 `suitable_for` 语义一致
- [ ] 已交 test-manager 审定（按模块独立放行）

## 触发与边界

**该用**：任何一次测试执行的**准备阶段**（建 RUN + 生成实例计划）。

**不该用**：
- 设计用例 → `case-design`；生成数据 → `test-data-gen`；用例结构化 → `case-structure`
- **执行实例、记录 EXEC、建 BUG** → `case-running`
- **审定实例计划** → `test-manager`
- 度量统计 → `test-rebuild`

## 常见错误

- **未审定就交给执行**（配对错误 = 整轮作废）。
- expected 留空或写成"见上"（无法判定）。
- plan_id 跨模块重号（EXEC 回指断裂）。
- 配对忽略 `suitable_for`（边界数据配正常用例，结论失真）。
- 顺手写执行结果（越界——结果属 EXEC）。
- RUN 未声明 envs 池（执行期无处租用环境）。
