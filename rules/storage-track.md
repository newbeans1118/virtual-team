# 存储规则（Storage Track）

本文件是 virtual-team 插件**测试数据存储的唯一规则源**：**JSON 单轨**（分片文件）。所有测试类技能（prd-structure / case-structure / test-data-gen / case-instantiate / case-running / test-rebuild）开工第一步读本文件。

> **单轨决策（务实化）**：早期版本提供 json / sqlite 双轨，实测 SQLite 轨需七表两触发器、校验覆盖不等价（JSON 轨 14 处 fail vs SQLite 轨 7 处）、九段指标 SQL 全为 `--` 注释样例且不可直接执行，对中小项目收益为负。故**统一为 JSON 单轨**，删除 SQLite 轨与 `SQLITE-SCHEMA.sql`。如确需 SQL 分析，由项目自行把 JSON 分片导入外部数据库，不纳入本插件契约。

> **机械校验**：产物结构与跨产物闭合由 `scripts/verify_artifacts.py <项目根> [--stage <阶段>]` 校验（schema 见 `schemas/`）：各分片格式、fail→BUG 回指、blocked→evidence、exec_id 全局唯一、plan_ref 同 RUN 回指、P0/P1 修复评审与验证证据、`--stage` 必需产物。门禁以退出码为准（discipline §14）。

## 0. 配置（唯一开关）

- `test/STORE-CONFIG.json` 由 **project-manager 立项时创建**（参考 `templates/STORE-CONFIG.json`），`store` **固定为 `json`**，**无需用户选轨**。
- **配置缺失 → FAIL**（`verify_artifacts.py` fail-closed，不代为默认创建）。
- 数据契约（实体 / 字段 / 关联）以 `schemas/` 下 8 个 JSON Schema 为唯一定义。

## 1. JSON 轨（唯一轨道）

机制数据全部为**分片文件**（并行写零冲突）：

| 数据 | 文件 | 生产者 |
|------|------|--------|
| PRD 侧 | `docs/prd/$COMPONENT/$MODULE/trace/prd.json` | prd-structure |
| 用例侧 | `test/trace/$COMPONENT/$MODULE/case.json` | case-structure |
| TD 注册表 | `test/trace/$COMPONENT/$MODULE/TD-REGISTRY.json` | test-data-gen |
| RUN 头 | `test/runs/RUN-xxx.json` | test-manager |
| 实例计划 | `test/runs/RUN-xxx/$COMPONENT/$MODULE/EXEC-PLAN.json` | case-instantiate（TM 审定） |
| 执行明细 | `test/runs/RUN-xxx/$COMPONENT/$MODULE/EXEC.jsonl`（追加式） | case-running |
| 缺陷 | `test/bugs/BUG-$COMPONENT-NNN.json` | case-running |

> **模块层可省**：组件不细分模块时（模块位 `all`），不建 `$MODULE/` 目录，分片直接放组件目录（`test/trace/workbench/case.json`）；文件名恒定，**不带模块位、不出现 `all`**（见 `team-charter` §2 模块层省略规则）。

- **EXEC 只追加**：不改写、不删除已写入行（由 `verify_artifacts.py` 的 exec_id 全局唯一与同文件查重机械保证）。
- **stale 判定**：git 提交对比（`prd.json` 提交早于 `prd.md` 提交 = 未同步）——结构文件不写 source_hash 副本到下游（PRD 分片写 `source_hash` 声明基线，case 分片写 `prd_source_hash`）。
- 累计 EXEC > 1 万行时，test-rebuild 先做聚合索引再计算。
