---
name: prd-structure
description: 把功能点结构化存储、供测试用例关联与追踪时使用。触发场景：需要从PRD抽取功能点清单、生成分片 prd.json、校验功能编号唯一性、建立PRD 侧追踪基线（source_hash）、需求变更后同步结构化数据、提到需求结构化、功能点清单、PRD 追踪。
---

# PRD 结构化存储（prd-structure）

## 目的

从 PRD 中提取功能点的结构化描述信息，**按组件/模块分片**存储，作为五方追踪（需求→用例→数据→执行→缺陷）的**PRD 侧锚点**。

## 执行者

`product-manager`

## 输入

- `docs/prd/$COMPONENT/$MODULE/prd.md`（组件不细分模块时省略 `$MODULE/`）

## 输出

- **JSON 轨**（默认）：`docs/prd/$COMPONENT/$MODULE/trace/prd.json`（**每模块一片**，禁止合并为单文件——并行写互不冲突）
- **JSON 轨模板**：`templates/PRD-STRUCTURE.json`

## 存储选择（开工第一步）

读 `rules/storage-track.md`（唯一规则源）+ `test/STORE-CONFIG.json`（`store=json`），**按 JSON 单轨规则**： 写分片文件 `docs/prd/$COMPONENT/$MODULE/trace/prd.json`；单轨只写分片文件。配置缺失 → BLOCKED 报 PM。

## 数据结构

```json
{
  "project": "$PROJECT_NAME",
  "component": "$COMPONENT",
  "module": "$MODULE",
  "version": 1,
  "updated_at": "",
  "source": "prd.md",
  "source_hash": "sha1:…",
  "functions": [
    {
      "id": "fr-$COMPONENT-$MODULE-001",
      "name": "功能名称",
      "biz_refs": ["biz-001"],
      "actor": "操作角色",
      "acceptance": [
        { "key": "c1", "given": "合法输入且状态允许", "when": "提交操作", "then": "返回成功且落库", "kind": "normal" },
        { "key": "c2", "given": "非法输入", "when": "提交操作", "then": "拒绝且不落库", "kind": "negative" }
      ],
      "constraints": ["…"],
      "status": "active | deprecated"
    }
  ]
}
```

**字段说明（五方关联视角）**：

| 字段 | 作用 |
|------|------|
| `functions[]` | **追踪锚，非全文**——功能完整描述（处理逻辑/输入输出/流程图）以该组件/模块的 `prd.md` 为权威源，按 fr 编号回溯 |
| `acceptance` | **验证条件条列（测试点）+ GWT**——每个功能点的验收标准拆为一组可判定的条件条目，是**测试点级覆盖率的分母**。条目 `{key, given, when, then, kind}`：`given/when/then` 三段（前置/操作/可观察结果，`then` 可判定）；`kind ∈ normal/boundary/negative`（供路径覆盖度派生）。**生成时对照 `prd` 技能的「acceptance 条件生成清单」与「FR 粒度五条检验」** |
| `biz_refs` | **归属关联**：本功能点**所属**的业务（业务=粗粒度价值，由多个功能点组成；fr 是细粒度可验收单元）。追溯读法：biz ← fr ← 用例 ← 执行。典型单元素；跨业务公共功能可多项 |
| `source_hash` | 写本分片 `source_hash` 声明 PRD 基线；stale 另由 git 提交对比判定（`prd.json` 提交早于 `prd.md` 提交 = 未同步） |
| `status: deprecated` | 需求删除时**标记废弃而非物理删除**——保住历史执行/缺陷记录的可回溯性 |
| ❌ **无 `verification_cases`** | 用例关联只存用例侧（`function_refs`）；反向视图由 `test-rebuild` 派生，**不双写** |
| ❌ **无 `change_log`** | 变更审计走 **git diff（PRD 内容级）+ hash 链（结构级 stale 判定）**，表/文件不重复承载 |

### acceptance 条目标识规则（防引用漂移，硬性）

- `key = "c" + 功能点内递增整数`（c1/c2/c3…）；全局标识 = `{fr-id}:{key}`，如 `fr-workbench-task_list-001:c2`。
- **只追加、不重排、不重用**：新增条件取当前最大 key+1；删除条件**保留 key 空缺**，不得重排剩余项（重排 = 下游用例 `acceptance_refs` 全部失配）。
- 向后兼容读取：`acceptance` 为**字符串**（旧数据）→ 降级视为**单条目** `{key:"c1", given:"", when:"", then:原文本, kind:"normal"}`；条目仅有 `text`（GWT 化前）→ 视为 `{given:"", when:"", then:text}`；为**空/缺失** → 计 0 条，报告标 `acceptance-missing`。
- 惰性升级：不强制改写旧数据；重跑时若检测到标量形态，输出提示 `[legacy] 功能点 fr-xxx 的 acceptance 为标量文本，建议拆分为条列以启用测试点级覆盖度量`。

> **变更回溯读法**：内容改了什么 → `git diff prd.md`；结构同步了吗 → source_hash 链 + test-rebuild 校验。表中字段是摘要快照，不承担内容级历史。

## 流程

1. 解析各组件/模块的 `prd.md`，抽取 `fr-$COMPONENT-$MODULE-NNN`。
2. 编号一律用 `scripts/id_alloc.py` 分配（`fr`/`biz`，`--component`/`--module`），**不手工编号**；分配后跑 `id_alloc.py . check` 校验唯一性与 snake_case 合规，冲突报告产品经理。
3. 计算 `source_hash`（PRD 文件内容哈希）。
4. 若已有旧分片：`version+1`、被删功能点置 `deprecated`（变更内容审计走 git diff PRD 文件）。
5. 写入分片文件。
6. 提示：下游 `case-structure` 需重新对齐 `prd_source_hash`。

## 质量要求

- 功能点信息与PRD一致，不得私自增删。
- **acceptance 必须条列化 + GWT 化**（每项 `{key, given, when, then, kind}`），`key` 只追加不重排不重用。
- 编号唯一、可检索。
- 与 `dict.md`、`overview.md` 的组件/模块清单一致。
- 分片独立合法（可被单文件解析）。

## 检查清单

- [ ] 所有功能点已抽取
- [ ] acceptance 已条列化 + GWT 化（key 唯一、given/when/then 完整、kind 合法、then 可判定）
- [ ] acceptance 条件按生成清单逐类对照（正常/边界/异常/权限/输入校验/状态约束；不适用已说明）
- [ ] 编号唯一且与规格一致
- [ ] `source_hash` 已计算
- [ ] 废弃项已标记 deprecated
- [ ] JSON 结构合法（可被解析）

## 触发与边界

**该用**：需求定稿后首次结构化；**需求变更后重跑**（hash 变化由 test-rebuild 校验发现）；验证条件变更后重跑（**仅追加 key，禁重排**）；**CR 变更单实施时重跑**（charter §5.1 变更闭环第④步——需求变更的下游同步起点）。

**不该用**：用例侧结构化 → `case-structure`；PRD 写作 → `prd`；覆盖率计算 → `test-rebuild`。

## 常见错误

- 抽取时私自增删功能点（必须与规格一一对应）。
- **acceptance 仍写整段文本**（应拆成条列——不拆则测试点级覆盖率无从计算）。
- **重排/重用已有 key**（下游用例 `acceptance_refs` 全部失配）。
- 需求变更后直接物理删除功能点（应 `deprecated`，否则历史 EXEC/BUG 悬空）。
- 忘记更新 `source_hash`（下游三方校验失效）。
- 合并成单一大文件（并行写冲突 + 检索低效）。
