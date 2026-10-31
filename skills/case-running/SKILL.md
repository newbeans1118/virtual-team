---
name: case-running
description: 执行已审定的测试实例、记录执行明细、提交并跟踪缺陷、移交度量与报告时使用。触发场景：需要按轮次执行测试、跑用例、调用加载脚本、记录 EXEC 执行明细、提交 BUG 并跟踪回归、产出轮次测试报告、提到执行测试、跑用例、回归测试、缺陷提交。
---

# 测试执行（case-running）

## 目的

**执行（run）**：消费**已审定的可执行实例**，把实例**跑掉**并记录结果。

即：**执行** = 实例 → 结果。随后失败成单（BUG）、回归闭环，并汇总本轮。执行明细只追加不改写，支撑度量复算与历史回溯。

> 与 `case-instantiate` 的分工：**本技能只执行**——实例（EXEC-PLAN）由 `case-instantiate` 生成、经 `test-manager` 审定后交来。

## 执行者

`test-engineer`（前置：实例计划已由 `test-manager` 审定）

## 输入

- **已审定的实例计划分片** `test/runs/RUN-xxx/EXEC-PLAN-$COMPONENT-$MODULE.json`（SQLite 轨：`exec_plans.approved=1` 的行）
- `test/runs/RUN-xxx.json`（RUN 头，test-manager 创建，含 `envs` 池——build/commit 引用**测试版构建产物**）
- 本分片 `test/trace/$COMPONENT/case-$MODULE.json`（用例与 automation 信息）
- `test/automation/`（`script_ref` 指向的自动化脚本）
- 测试版构建产物 + `release/manual-install.md`（环境部署依据；**测试环境必须来自测试版构建，不得用开发工作区充当**——缺失 → BLOCKED 报 PM）

## 输出（按存储轨道 × 分片）

**分片规则**：执行分片 = **组件/模块**（一分片一文件，彻底避免同文件并发写）。**env 是执行期从 `RUN.envs` 池中独占租用的资源**——分片执行时租用一个 env、期间锁定、结束（含清理）后释放；红线：**同一 env 同一时刻只允许一个分片占用**，故**同时活跃的分片数 ≤ `RUN.envs` 数**。同一分片可先后在多个 env 执行（EXEC 行以 `env` 字段区分）。

- **JSON 轨**（默认）：
  - `test/runs/RUN-xxx/EXEC-$COMPONENT-$MODULE.jsonl`（本分片执行明细，**追加式**——分片文件互不交叉，多实例并行零冲突）
  - `test/bugs/BUG-xxx.json`（缺陷单）
  - `test/report/RPT-xxx.md`（轮次测试报告）
  - 更新本分片 `test/trace/$COMPONENT/case-$MODULE.json` 的 `latest_result_ref`
- **SQLite 轨**（STORE-CONFIG.store=sqlite）：写 `test/trace/metrics.db`
  - `execs` 表（**只追加**，由触发器强制：UPDATE/DELETE 直接 ABORT）
  - `bugs` 表
  - 更新 `cases.latest_result_ref` 列

> **注意**：RUN 头（含 envs 池）由 test-manager 创建，本技能**只读不写** RUN 头；轮次汇总（total/pass/fail/blocked）**不回写 RUN**——由 `test-rebuild` 从 EXEC 明细派生（消除多分片并发回填单文件的竞态与双写）。

## 存储选择（开工第一步）

读 `test/STORE-CONFIG.json`——**项目立项时已一次性选定，全程跟随；仅允许一次 json→sqlite 单向迁移**（迁移后不可逆）。
- `store=json` → 写文件（EXEC-<组件>-<模块>.jsonl / BUG / RPT）。
- `store=sqlite` → 入库（`execs` 只追加触发器强制；`bugs`）。
- 配置缺失 → **BLOCKED 报项目经理**（立项时未完成存储决策，不得代为默认选轨）。**数据契约（实体/字段/关联）两轨完全一致，仅读写方式不同。**

## 流程（五步，顺序固定）

### 1. 核对前置

- 确认本分片 EXEC-PLAN **已经 TM 审定**（JSON 轨：`approved_by` 非空；SQLite 轨：`exec_plans.approved=1`）。**未审定 → BLOCKED 报项目经理，不得开跑。**
- 从 `RUN.envs` 池**独占租用一个 env**（同 env 同刻单占用）；记录租用。

### 2. 执行（本分片 = 本组件/模块 × 租用的 env）

逐实例执行：
1. 调用该行 TD 的 `load_entry`（加载数据；不解释内容，照单调用）。
2. 执行用例步骤——**若该用例 `automation.script_ref` 存在则调用自动化脚本，否则人工按步骤执行**。
3. **追加**一行 EXEC 到本分片 `RUN-xxx/EXEC-$COMPONENT-$MODULE.jsonl`：`{exec_id, plan_ref, run, case, td, env, result, defect_ref, started_at, duration_ms, evidence}`。
   - **exec_id = 复合格式 `{plan_ref}-{seq}`**（如 `P-003-1`）：seq 为同一实例的重跑序号（首次=1，重跑+1）。plan_ref 全局唯一 → exec_id 全局唯一，**并行分片零撞号、无需集中分配**；同实例多次重跑的行天然聚合。
4. 无论成败，按数据单元的清理逻辑恢复环境（**恢复到环境基线态**——`test/baseline/` 定义部署级初始态；TD 清理只清本单元数据，不清基线种子数据）。

> 单行失败**继续下一行**（除非冒烟轮核心失败才中止）——保持轮次完整性。
> **env 独占**：本分片执行期间独占租用的 env；结束（含清理完成）后释放，归还 `envs` 池。

### 3. 提交缺陷

- **失败 EXEC（result=fail）** → 建 `BUG-xxx.json`（模板 `templates/BUG.json`）：**必须回指** `{exec, run, case, td}`（度量分母的依据）；状态机 `open → in_fix → fixed → verify_pass → closed`，`verify_fail` 重开并记 `reopen_count`。
- **阻塞 EXEC（result=blocked）** → 判定条件：环境不可用、依赖缺失、前置数据无法加载等**非被测软件缺陷**的原因导致无法执行。**不建 BUG**，但须在 EXEC 的 `evidence` 写明阻塞原因；该行**不计入通过率分子分母**，单列「阻塞统计」交 test-manager 评估（是否需要换 env 重跑）。

### 4. 回归验证

修复后开 `trigger=defect-verify` 的新 RUN（由 `case-instantiate` 生成实例计划、TM 审定），只跑相关实例行；**按 BUG 组分片**——验证范围天然隔离，可多实例并行（仍受同 env 单租约束）；`verify_pass` 才能关闭缺陷。**验证由测试侧做，开发者不得自行关闭**。

> **verify_pass 判定**：该 BUG 关联的全部实例行重跑后 **result=pass** → `verify_pass`；**任一行仍 fail** → `verify_fail`（重开，`reopen_count+1`）。部分修复不得判通过。

### 5. 汇总与移交

- **汇总归属**：轮次汇总（total/pass/fail/blocked）**不回写 RUN 头**——由 `test-rebuild` 从全部分片 EXEC 派生（只派生不回写，防并发竞态与双写）。
- 更新用例侧 `latest_result_ref` 指针（各分片实例更新自己模块的）。
- 触发 `test-rebuild` 生成度量报告（消费全部分片），交 `test-manager` 评估。
- 按 `templates/TEST-REPORT.md` 产出本轮**测试报告** `test/report/RPT-$RUN.md`（人工可读的轮次总结；与 test-metrics 度量报告并存——前者面向交付、后者面向度量），交 `test-manager` 汇总。

## 分片粒度决策规则

- **默认**：一组件/模块一执行分片（一文件）。
- **分片过大**（实例行 > 200）：可拆"组件 × 子域"，分片键 `$COMPONENT-subdomain`。
- **分片过小**（实例行 < 10）：并入相邻分片，避免实例数爆炸（并发上限 20 同样适用）。
- **并发上限**：**同时活跃分片数 ≤ `RUN.envs` 数**（env 是独占租用资源）。

## 质量要求

- **未审定的 EXEC-PLAN 不得执行**；EXEC **只追加不改写**。
- 每条 EXEC 必须回指实例行（plan_ref）——度量可复算的前提；exec_id 用复合格式 `{plan_ref}-{seq}`（plan_ref 全局唯一 → 零撞号）。
- 数据加载必须经 `load_entry`，**禁止绕过直接改环境**（保证配对与执行的对应）。
- BUG 必须回指 exec（否则修复率无分母）。
- **env 独占**：同一 env 同一时刻只允许一个分片租用；分片实例**只写本分片产物**（EXEC-<组件>-<模块>.jsonl / 本分片 case 分片）。
- **不越界**：本技能不改实例计划（修正配对须回 `case-instantiate` 重新生成并审定）、不回写 RUN 头（轮次汇总由 test-rebuild 派生）。

## 检查清单

- [ ] 确认 EXEC-PLAN 已审定（否则 BLOCKED）
- [ ] 已从 envs 池独占租用 env，且活跃分片数 ≤ env 数
- [ ] EXEC 只追加、逐行回指 plan_ref、exec_id 为复合格式、含 env 字段、落在各自分片文件
- [ ] 失败项全部建 BUG 且回指 exec；blocked 项已记原因且不计入通过率
- [ ] 回归轮已跑、verify 结果已回写 BUG
- [ ] latest_result_ref 已更新、未回写 RUN 头（汇总由 test-rebuild 派生）
- [ ] RPT-xxx 测试报告已产出
- [ ] test-rebuild 已触发

## 触发与边界

**该用**：实例计划已审定，要执行并记录结果时。

**不该用**：
- 建 RUN 头 → `test-manager`；在 RUN 内生成实例计划 → `case-instantiate`
- 设计用例 → `case-design`；生成数据 → `test-data-gen`
- **审定实例计划** → `test-manager`
- 度量统计（含轮次汇总）→ `test-rebuild`
- 修改缺陷状态为 closed → 须 verify_pass 证据，且由流程驱动，不跳步

## 常见错误

- **未审定就开跑**（配对错误 = 整轮作废）。
- EXEC 改写历史行（度量失去复算基础）。
- exec_id 用集中自增号（并行分片撞号；应用 `{plan_ref}-{seq}` 复合格式）。
- 绕过 load_entry 手工造数据（EXEC 与 TD 的对应断裂）。
- 失败不建 BUG 或 BUG 不回指 exec（修复率分母丢失）。
- blocked 当 fail 处理（误建 BUG）或当通过处理（掩盖环境问题）。
- 开发者自行关闭缺陷（验证权在测试侧）。
- 回写 RUN 头的 summary（多分片竞态 + 与 test-rebuild 双写；汇总应派生）。
