---
name: case-instantiate
description: 在 test-manager 已建的执行轮（RUN）内、按组件/模块把用例与数据单元配对生成可执行实例（执行实例计划）时使用。触发场景：需要按轮次组织测试、在既定 RUN 内把静态用例与 TD 数据配对成可执行实例、产出 EXEC-PLAN-模块.json 并交 test-manager 审定、提到生成执行计划、实例化、用例数据配对、执行轮准备。
---

# 测试实例化（case-instantiate）

## 目的

**实例化（instantiate）**：把**静态资产**（用例 + 数据单元）转成**可执行实例**。

- 一个 `用例 × 数据` = 一个**可执行实例**（EXEC-PLAN 行）；`expected` 是实例的属性。
- 本技能只做**准备**：配对生成实例 → 交审定。**不执行**（执行属 `case-running`）。

> 与 `case-running` 的分工：**本技能产出实例计划（设计型产物，需审定）**；`case-running` 消费它并产出执行明细（运行型产物，追加式）。
> **RUN 头由 test-manager 创建**（建头：id/trigger/scope/envs/defect_refs，含执行派发建议交 PM）——本技能在 TM 已建的 RUN 内配对，**不建头**（消除多分片并发建头的竞态）。

## 执行者

`test-engineer`（RUN 头由 `test-manager` 创建；实例计划由 `test-manager` 审定）

## 输入

- **已存在的 RUN 头** `test/runs/RUN-xxx.json`（test-manager 创建：id/trigger/defect_refs/scope/envs）
- `test/plan.md`（测试方案，含范围与环境要求）
- 本分片 `test/trace/$COMPONENT/case-$MODULE.json`（用例分片，含 `function_refs`/`acceptance_refs`/`dataset_refs`）
- 本分片注册表 `test/trace/$COMPONENT/TD-REGISTRY-$MODULE.json`（SQLite 轨：查库）
- `docs/prd/$COMPONENT/$MODULE/trace/prd.json`（acceptance 文本，expected 来源之一）

## 输出（按存储轨道 × 分片）

**分片规则**：实例计划**按组件/模块分片**——一个 test-engineer 实例只负责一个 `$COMPONENT/$MODULE`，只产出本分片实例计划；多实例并行零交叉。

- **JSON 轨**（默认）：
  - `test/runs/RUN-xxx/EXEC-PLAN-$COMPONENT-$MODULE.json`（本分片实例计划，**TM 审定后生效**）
- **SQLite 轨**（STORE-CONFIG.store=sqlite）：写 `test/trace/metrics.db`
  - `exec_plans` 行（plan_id / module / run_id / case_id / td_id / expected / source / approved=0）
  - `approved` 列承载 TM 审定标记（未审定行禁止执行）

## 存储选择（开工第一步）

读 `rules/storage-track.md`（唯一规则源）+ `test/STORE-CONFIG.json`，**只加载所选轨道一节的规则**：`store=json` → 写 `EXEC-PLAN-$COMPONENT-$MODULE.json`；`store=sqlite` → 写 `exec_plans` 行。配置缺失 → BLOCKED 报 PM。（RUN 头由 test-manager 创建，本技能不建头。）

## 执行轮类型（trigger）

| 类型 | 范围 | 触发时机 |
|------|------|---------|
| `full` | 全部 active 用例 | 首轮 / 交付前 |
| `regression` | 修复相关 + 核心路径 | 缺陷修复后 / 里程碑 |
| `smoke` | 核心冒烟集 | 每次部署后 |
| `defect-verify` | 指定 BUG 的验证用例 | 修复完成后（`defect_refs` 必填） |

## 流程（三步，顺序固定）

### 1. 核对 RUN 头（test-manager 已建）

- 确认 `test/runs/RUN-xxx.json` 存在且由 test-manager 创建（含 `envs` 池声明，每项 build/commit 引用**测试版构建产物**——证据）。
- **RUN 头缺失 → BLOCKED 报项目经理**（TM 未建头，不得由本技能代建——多分片并发代建会撞头）。

### 2. 配对生成实例（按模块分片，**逐验证条件**）

配对单位是「**用例 × 验证条件 × TD**」——kind 从PRD 侧派生，不加新字段：

- **kind 派生**：用例的 kind 需求 = 其 `acceptance_refs` 所引验证条件在 PRD 侧 `acceptance[].kind`（单一事实源在 req，派生不双写）。
- **逐条件配对**：对本分片每个 active 用例引用的每个验证条件（kind=k），从其 `dataset_refs` ∩ TD 注册表中 `suitable_for` 含 k 的数据单元里选定配对，生成一行 `{plan_id, case, condition, td, expected, source}`：
  - **`condition`**：`{fr-id}:{key}`（该实例验证的条件标识，如 `fr-workbench-task_list-001:c2`）——EXEC 与 BUG 回指的锚点。
  - **`expected`** 是实例属性——**优先取该条件 GWT 的 `then`**（source=acceptance）；也可从用例预期语义 / TD 单元 `expected_hints` 提炼，或项目补充；**同一 TD 配不同条件预期不同**。
  - **`source`** 取值：`acceptance | case-expected | expected-hints | manual`（acceptance 为优先来源）。
  - **`plan_id`（P-xxx）全局唯一（跨 RUN）**——TM 审定时全局查重（含历史 RUN）；EXEC 的 `plan_ref` 与复合格式 exec_id 据此回指。
- **一用例跨多 kind** → 每个条件各生成实例行，各行挂 kind 匹配的 TD（dataset_refs 本就是数组，天然支持）。
- **fallback（未声明 acceptance_refs 的用例）**：功能点级配对——从 `dataset_refs` 中选 `suitable_for` 含 normal 的 TD，`condition` 置 null、source 标 `manual`；缺口报告呈现（point-untagged）。
- 参考用例侧 `dataset_refs`（该用例声明的可用数据单元）与 TD 侧 `owner_cases`（双向一致），确定候选集。
- 产出**本分片实例计划** `EXEC-PLAN-$COMPONENT-$MODULE.json`。

### 3. 提交审定

- 交 `test-manager` **审定**：配对合理性（**逐条件 kind 匹配**：condition 的 kind ∈ TD.suitable_for）、expected 完整性、**plan_id 全局唯一性（跨片 + 跨历史 RUN 查重）**。
- **按模块分片独立放行**（不要求等齐全部模块——避免同步屏障；跨片由审定时的全局查重保障）。
- **未经审定不得进入执行**（`case-running` 的前置硬门禁）。

## 质量要求

- 每个 active 用例引用的每个验证条件（`acceptance_refs` 项）都应有 kind 匹配的实例行；未形成须说明理由（fallback 行除外，单独标注）。
- `plan_id` 全局唯一（跨 RUN）；`expected` 非空且可判定（acceptance 来源优先）。
- 配对必须逐条件 kind 匹配（condition 的 kind ∈ TD 的 `suitable_for`——boundary 条件不配 normal 数据）。
- **不越界**：本技能不建 RUN 头（TM 职责）、不执行、不记录结果（属 `case-running`）。
- 分片只写本分片产物，不改其他实例分片。

## 检查清单

- [ ] RUN 头已存在（test-manager 创建，含 `envs` 池与 build/commit 证据；缺失 → BLOCKED）
- [ ] 本分片实例计划已生成
- [ ] 每行含 plan_id/case/condition/td/expected/source，plan_id 全局唯一（跨 RUN）
- [ ] 每行 condition 的 kind 与 TD.suitable_for 匹配；fallback 行已单独标注
- [ ] expected 非空、可判定、来源标注正确（acceptance 优先）
- [ ] 已交 test-manager 审定（按模块独立放行）

## 触发与边界

**该用**：任何一次测试执行的**准备阶段**（在 TM 已建的 RUN 内生成实例计划）。

**不该用**：
- 设计用例 → `case-design`；生成数据 → `test-data-gen`；用例结构化 → `case-structure`
- **建 RUN 头（trigger/scope/envs 决策）** → `test-manager`
- **执行实例、记录 EXEC、建 BUG** → `case-running`
- **审定实例计划** → `test-manager`
- 度量统计 → `test-rebuild`

## 常见错误

- **RUN 头缺失时代为建头**（多分片并发代建 = 撞头竞态；应 BLOCKED 报 PM）。
- **未审定就交给执行**（配对错误 = 整轮作废）。
- **按用例整体配对而忽略条件 kind**（boundary 条件配了 normal 数据，结论失真）。
- expected 留空或写成"见上"（无法判定）。
- plan_id 跨模块或跨 RUN 重号（EXEC 回指断裂、exec_id 撞号）。
- 顺手写执行结果（越界——结果属 EXEC）。
- 未声明 acceptance_refs 的用例不做 fallback 标注（配对依据不可追溯）。
