---
name: case-structure
description: 把测试用例结构化存储并与功能点、数据单元关联时使用。触发场景：需要生成分片 case-$MOD.json、建立用例与功能编号（CASE↔fr）及数据单元（dataset_refs）的双向关联、登记 automation 自动化信息、检测孤立用例与未覆盖功能点、提到用例结构化、用例关联、覆盖率。
---

# 测试用例结构化（case-structure）

## 目的

将测试用例结构化存储，**一端关联功能点（需求侧），另一端关联数据单元（数据侧）**——用例是五方追踪（需求→用例→数据→执行→缺陷）的**中枢节点**。

## 执行者

`test-engineer`

## 输入

- `test/cases/CASE-xxx.md`
- `docs/requirements/trace/req-$MOD.json`（需求侧锚）
- 本模块注册表分片 `test/data/trace/TD-REGISTRY-$MOD.json`（数据侧锚，若已生成；SQLite 轨=查库）

## 输出（按存储轨道）

- **JSON 轨**（默认）：`test/trace/case-$MOD.json`（**每模块一片**，与 req 分片对称）
- **SQLite 轨**：写 `test/trace/metrics.db` 的 `cases` 表（module 列保留分片语义；字段一一对应；DDL 见 `templates/SQLITE-SCHEMA.sql`）

## 存储选择（开工第一步）

读 `test/STORE-CONFIG.json`——**项目立项时已一次性选定，全程跟随；仅允许一次 json→sqlite 单向迁移**（迁移后不可逆）。
- `store=json` → 写分片文件 `test/trace/case-$MOD.json`。
- `store=sqlite` → UPSERT `cases` 表（module 列承载分片语义）。
- 配置缺失 → **BLOCKED 报项目经理**（立项时未完成存储决策，不得代为默认选轨）。**数据契约（实体/字段/关联）两轨完全一致，仅读写方式不同。**

## 数据结构

```json
{
  "project": "$PROJECT_NAME",
  "module": "$MOD",
  "updated_at": "",
  "req_source_hash": "sha1:…",
  "cases": [
    {
      "id": "CASE-xxx",
      "title": "用例标题",
      "function_refs": ["fr-$MOD-xxx"],
      "acceptance_refs": ["fr-$MOD-xxx:c1"],
      "dataset_refs": ["TD-xxx"],
      "type": "functional | performance | security | compatibility",
      "priority": "P0 | P1 | P2",
      "status": "draft | active | deprecated",
      "preconditions": ["…"],
      "automation": { "automatable": false, "script_ref": null, "last_verified_run": null },
      "latest_result_ref": "test/runs/RUN-xxx/EXEC-$MOD.jsonl#L3"
    }
  ]
}
```

**字段说明（五方关联视角）**：

| 字段 | 关联方向 | 说明 |
|------|---------|------|
| `function_refs` | 用例 → 需求 | **数组**（一用例可验多功能点）；反向视图由 `test-rebuild` 派生 |
| `acceptance_refs` | 用例 → 验证条件 | **数组**，引用 `{fr-id}:{key}`（如 `fr-user-auth-001:c2`）；**只存标识不复制文本**（文本单点在 req 侧 acceptance）。**引用闭合**：每项前缀 fr-id 必须已在本用例 `function_refs` 中。空数组 = 仅功能点级覆盖（标 `point-untagged`） |
| `dataset_refs` | 用例 → 数据 | 本用例可用的数据单元；**必须与 TD 注册表的 `owner_cases` 双向一致** |
| `req_source_hash` | 源同步 | 声明"基于哪版需求结构化"；与 req 分片 hash 不一致 = stale |
| `automation` | 复用支撑 | `automatable` + `script_ref`（自动化脚本路径）+ 最近验证轮。**case-running 执行时若 script_ref 存在则调用该脚本，否则人工按步骤执行** |
| `latest_result_ref` | 用例 → 执行 | **指针**不存值；最近一次执行明细在本模块 EXEC-$MOD.jsonl 分片中 |
| ❌ **无 `result` 字段** | — | 执行结果只存 EXEC（追加式），用例是静态资产 |

## 流程

1. 解析用例文件，抽取结构化字段。
2. `function_refs` 对齐 req 分片——检测**孤立用例**（引用不存在的功能点）。
3. `acceptance_refs` 对齐 req 分片的 `acceptance[].key`——检测**悬空引用**（指向不存在的验证条件）与**引用闭合违规**（fr-id 不在本用例 function_refs 中）。
4. `dataset_refs` 对齐 TD 注册表——检测**无数据用例**（无法执行的假覆盖）；并与注册表 `owner_cases` 双向核对。
5. 登记 `automation` 信息（可自动化的标注 script_ref）。
6. 计算并写入 `req_source_hash`。
7. 输出分片；未覆盖功能点、孤立用例、悬空引用、缺数据用例**显式列出**报 `test-manager`。

## 质量要求

- 每个 `function_refs` 必须存在于 req 分片（孤立用例 = P0）。
- 每个 `acceptance_refs` 必须存在于对应功能点的 `acceptance[].key`（悬空引用 = 告警，列遗留风险）；引用闭合（前缀 fr-id ∈ function_refs）。
- 每个 active 用例必须有 ≥1 个 `dataset_refs`（无数据 = 无法执行的假覆盖）。
- 覆盖缺口**显式列出，禁止标"通过"**。
- 与 req 分片 hash 对齐（stale 时提示 req-structure 重跑）。

## 检查清单

- [ ] 所有用例已结构化（分片）
- [ ] function_refs 全部有效（无孤立）
- [ ] acceptance_refs 无悬空、引用闭合
- [ ] dataset_refs 与 TD 注册表双向一致
- [ ] automation 信息已登记
- [ ] req_source_hash 已写入
- [ ] 覆盖缺口已显式报告

## 触发与边界

**该用**：用例写完后结构化；TD 生成后补 `dataset_refs`；需求变更后重跑（hash 失配时）。

**不该用**：设计用例 → `case-design`；生成数据 → `test-data-gen`；需求侧结构化 → `req-structure`；覆盖率与度量 → `test-rebuild`。

## 常见错误

- 孤立用例不报告（function_ref 指向不存在的功能点）。
- **在用例侧复制 acceptance 文本**（只能引标识——文本单点在 req 侧，复制即双写漂移）。
- **acceptance_refs 引用闭合违规**（前缀 fr-id 未列在本用例 function_refs 中）。
- 有用例无数据却计入覆盖率（假覆盖）。
- `owner_cases` 与 `dataset_refs` 单边修改（双向关联断裂）。
- 把执行结果写进用例结构（应由 EXEC 承载，历史不可变）。
- 合并单一大文件（并行写冲突）。
