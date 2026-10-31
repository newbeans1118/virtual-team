# 存储轨道规则（Storage Track）

本文件是 virtual-team 插件**测试数据双轨存储（json / sqlite）的唯一规则源**。所有测试类技能（prd-structure / case-structure / test-data-gen / case-instantiate / case-running / test-rebuild）**开工第一步读本文件**——按 `test/STORE-CONFIG.json` 选定的轨道，**只读对应一节的规则**（另一节不加载）。

> **机械校验**：两轨产物的结构与跨产物闭合由 `scripts/verify_artifacts.py <项目根>` 机械校验（schema 见 `schemas/`）：JSON 轨校验各分片格式、fail→BUG 回指、blocked→evidence、exec_id 全局唯一、plan_ref 闭合；SQLite 轨校验机制七表、execs 只追加触发器、td_biz_* 孤儿、关闭缺陷的验证与修复评审证据。门禁以退出码为准（discipline §14 同一哲学）。

## 0. 选轨与迁移（唯一开关）

- `test/STORE-CONFIG.json` 由 **project-manager 立项时与用户一次性选定**（参考 `templates/STORE-CONFIG.json` 的选轨指引），全程跟随。
- **配置缺失 → BLOCKED 报项目经理**（立项时未完成存储决策，不得代为默认选轨）。
- **仅允许一次 json→sqlite 单向迁移**（迁移后 `store` 固定为 sqlite，`migrated_from` 记录源与时间；不可逆）。
- **禁止两轨混写、禁止默认选轨**。
- **数据契约（实体/字段/关联）两轨完全一致，仅读写方式不同。**

## 1. JSON 轨（store=json）

**适用场景**：单项目执行量 <1 万、需 git diff 审计。机制数据全部为**分片文件**（并行写零冲突）：

| 数据 | 文件 | 生产者 |
|------|------|--------|
| PRD 侧 | `docs/prd/$COMPONENT/$MODULE/trace/prd.json` | prd-structure |
| 用例侧 | `test/trace/$COMPONENT/case-$MODULE.json` | case-structure |
| TD 注册表 | `test/trace/$COMPONENT/TD-REGISTRY-$MODULE.json` | test-data-gen |
| RUN 头 | `test/runs/RUN-xxx.json` | test-manager |
| 实例计划 | `test/runs/RUN-xxx/EXEC-PLAN-$COMPONENT-$MODULE.json` | case-instantiate（TM 审定） |
| 执行明细 | `test/runs/RUN-xxx/EXEC-$COMPONENT-$MODULE.jsonl`（追加式） | case-running |
| 缺陷 | `test/bugs/BUG-$COMPONENT-NNN.json` | case-running |

- **stale 判定**：git 提交对比（`prd.json` 提交早于 `prd.md` 提交 = 未同步）——结构文件不写 source_hash 副本到下游（PRD 分片写 `source_hash` 声明基线，case 分片写 `prd_source_hash`）。
- 累计 EXEC > 1 万行时，test-rebuild 先做聚合索引再计算。

## 2. SQLite 轨（store=sqlite）

**适用场景**：预期执行量大、需任意维度 SQL 切片、业务数据需 SQL 复用。`test/trace/metrics.db` 为**唯一权威存储**（五方机制数据 + TD 业务数据全部入库；人读走按需 SQL，无快照导出）：

| 数据 | 表 | 说明 |
|------|-----|------|
| PRD 侧 | `prd_functions` | component+module 双列承载分片语义；**source_hash 行内自证**（.db 不可 git diff） |
| 用例侧 | `cases` | module 列承载分片语义；prd_source_hash 同上 |
| TD 注册表 | `td_registry` | 字段与 JSON 轨一一对应 |
| TD 业务数据 | `td_biz_*`（业务表） | **必含 `td_id` 外键关联 `td_registry(id)`**——无关联行 = 孤儿（P0）；删除 TD 级联清理业务行 |
| RUN 头 | `runs` | envs 列为 JSON 数组（build/commit 引用测试版构建产物） |
| 实例计划 | `exec_plans` | plan_id 单列主键（全局唯一）；`approved` 承载 TM 审定标记 |
| 执行明细 | `execs` | **只追加**（库级触发器禁 UPDATE/DELETE） |
| 缺陷 | `bugs` | 状态机同 JSON 轨 |

- **建库**：DDL 见 `templates/SQLITE-SCHEMA.sql`（含触发器与八项指标 SQL）；首次建库由 prd-structure/case-structure/test-data-gen 的执行角色执行——**建库与查库动作要求执行角色持 Bash 工具**（product-manager / test-engineer / test-manager 均已具备，见各 agent frontmatter）。
- **加载脚本不入库**：`test/data/$COMPONENT/scripts/TD-xxx-load.*` 仍单独存文件（职责：从业务表 SELECT → 装入被测系统；幂等 + 可清理）；`load_entry` 登记脚本路径。
- **审定动作** = 查库核对（`td_registry` 行、`exec_plans.approved` 标记；只读 SELECT，由持 Bash 的角色执行）。
- **两轨混用 = 违规**：建了业务表仍把数据写文件、或 JSON 轨项目写 metrics.db，均为红线。

## 3. 迁移（json→sqlite，一次性）

由 PM 派发 test-engineer 执行（迁移动作本身属测试资产变更，走 CR 或测试方案变更）：
1. 建库（SQLITE-SCHEMA.sql）。
2. 全量分片文件入库（PRD/case/TD/RUN/EXEC-PLAN/EXEC/BUG 七类，行级 INSERT）。
3. TD 数据本体从文件迁入业务表 `td_biz_*`（含 td_id 外键）。
4. 校验：test-rebuild 跑五项一致性校验，数字与迁移前 JSON 侧一致。
5. 更新 STORE-CONFIG（store=sqlite + migrated_from 留痕）——此后 JSON 分片文件冻结为历史归档，不再更新。
