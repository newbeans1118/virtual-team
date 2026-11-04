---
name: test-data-gen
description: 生成测试数据单元并登记供用例引用时使用。触发场景：需要按功能验收标准与测试用例设计测试数据、编写数据加载脚本、登记 TD 注册表、为一份数据关联多个用例（owner_cases）、提到测试数据准备、数据单元、数据集生成、加载方法。
---

# 测试数据生成（test-data-gen）

## 目的

把"测试需要什么数据"变成**可加载、可复用、可追溯**的数据单元（TD-$COMPONENT-NNN），并以**黑盒**形式登记——机制层只见 `{id, description, load_entry}`，业务血肉留在单元内部。

## 执行者

`test-engineer`（由 PM 派发；`test-manager` 审定登记表）

## 输入

- `docs/prd/$COMPONENT/$MODULE/trace/prd.json`（功能验收标准）
- `test/cases/$COMPONENT/CASE-$COMPONENT-NNN.md`、`test/trace/$COMPONENT/$MODULE/case.json`（用例意图）
- `test/plan.md`（测试范围与环境约束）
- `design/INTERFACE.md`、`design/$COMPONENT/database.md`（本组件表结构）、`design/$COMPONENT/func.md`（或 `$MODULE/func.md`）；全局数据规范见 `design/DATABASE.md` §2（加载方法的依据，只读）

## 输出（按分片）

**分片规则**：数据生成**按组件/模块分片**——一个 test-engineer 实例只负责一个 `$COMPONENT/$MODULE` 的 TD，产出该分片注册表；多实例并行时零交叉（红线：**只写本分片产物**）。

- **JSON 轨**（默认）：
  - `test/data/$COMPONENT/TD-$COMPONENT-NNN/`（数据文件+加载脚本）
  - `test/trace/$COMPONENT/$MODULE/TD-REGISTRY.json`——**注册表分片**（每组件/模块一片，与 case/PRD 分片对称；全局视图由 test-rebuild 合并，禁止实例间互相改写对方分片）
  - **加载脚本仍单独存文件**：`test/data/$COMPONENT/scripts/TD-$COMPONENT-NNN-load.*`——职责为"从业务表 SELECT 数据 → 装入被测系统"；`load_entry` 登记该脚本路径
  - 配套清理脚本（DELETE 该 td_id 业务行 + 环境回收）

## 存储选择（开工第一步）

读 `rules/storage-track.md`（唯一规则源）+ `test/STORE-CONFIG.json`（`store=json`），**按 JSON 单轨规则**写文件（TD 目录 + 注册表分片）。配置缺失 → BLOCKED 报 PM。


## 前置（硬门禁，缺任一 → BLOCKED 报 PM）

1. 需求定稿且已结构化（本分片 `prd.json` 存在）。
2. 用例已设计并结构化（本分片 `case.json` 存在，owner 用例明确）。
3. 测试方案已经用户确认（`test/plan.md`）。
4. 设计文档可读（加载方法依据）。
5. **测试版构建产物可用**（`release/artifact/` + `release/manual-install.md`，代码评审闭环后由 release-engineer 产出）——**加载脚本必须在其上实测跑通**，验证记录写入注册表分片。设计 TD 与加载脚本可与编码并行，实测须待测试版构建完成。

## TD 单元黑盒规范（核心）

注册表中每个条目的**机制可见部分为顶层字段** `id` / `description`（六字段）/ `load_entry` / `verified`，机制层不解释 description 内容：

```json
{
  "id": "TD-$COMPONENT-NNN",
  "description": {
    "purpose": "这组数据验证什么场景（一句话）",
    "suitable_for": ["normal | boundary | negative 中的若干（与PRD 侧 acceptance.kind 同枚举）"],
    "preconditions": ["对环境/前置的要求"],
    "data_scope": "覆盖/不覆盖的范围说明（防误配对）",
    "owner_cases": ["CASE-$COMPONENT-NNN", "..."]
  },
  "load_entry": "test/data/$COMPONENT/TD-$COMPONENT-NNN/load.sh",
  "verified": { "command": "加载命令", "result": "pass | fail", "at": "" }
}
```

**六字段语义**：

| 字段 | 必填 | 说明 |
|------|------|------|
| `purpose` | ✅ | 语义锚点，配对评审的依据 |
| `suitable_for` | ✅ | **配对匹配键**——值域 `normal/boundary/negative`，与PRD 侧 `acceptance.kind` **同枚举**；`case-instantiate` 按「用例引用的验证条件 kind」逐条件匹配。**混合场景底座用数组多值表达**（如 `["normal","negative"]` 即组合底座），不设独立 combination 值 |
| `preconditions` | ✅ | 执行前检查项，避免脏跑 |
| `data_scope` | 共享时必填 | 明确"不覆盖什么"，防止误配对 |
| `owner_cases` | ✅ 数组 | 引用本单元的**全部**用例（可跨组件/模块）；一份数据可服务多个用例（不同用例产生不同结果，预期在执行计划中落定） |
| `load_entry` | ✅ | 可执行入口（脚本路径/命令）；**加载方法业务相关，由本技能设计**，机制层只照单调用 |

**禁止写入**（红线）：
- ❌ `expected`——预期结果属于**执行计划配对行**，不属数据单元（一数据多用例时预期各不相同）。
- ❌ 业务字段值/业务实体名——数据本体在 `test/data/$COMPONENT/TD-$COMPONENT-NNN/` 内部文件里，机制不可见。
- ❌ `suitable_for` 使用 `normal/boundary/negative` 之外的值（如 combination）——枚举游离将使 kind 匹配失效。

## 流程

1. **对齐用例**：逐个用例分析"验证它需要什么数据场景"（正常/边界/异常/组合）。
2. **判定单元粒度**：一个场景底座 = 一个 TD；**多用途场景标记多 owner**（`owner_cases` 数组）——如"资源临界状态"数据可同时服务"操作拦截""计数校验""余量归零"三类用例。
3. **设计数据内容**：写 `test/data/$COMPONENT/TD-$COMPONENT-NNN/` 内部文件（业务相关，形态项目自定：JSON/CSV/脚本生成均可）。
4. **编写加载方法**：`load_entry` 可执行脚本——负责"把数据装入被测系统"（走 API / 数据库 / 静态配置，依设计文档定）；**必须幂等**（重复加载不残留），配套清理逻辑。
5. **实测验证**：执行 `load_entry`，确认加载成功且可清理；验证命令与结果写入注册表 `verified` 字段。
6. **登记**：更新本分片注册表 `TD-REGISTRY.json`（编号由 `scripts/id_alloc.py . td --component $COMPONENT` 分配，**不手工编号**；description 六字段；owner_cases 与本分片 `case.json` 双向一致）。
7. **提交审定**：注册表交 `test-manager` 审定（description 规范性、加载入口可执行、owner_cases 完整）。

## 质量要求

- 每个引用了 TD 的用例，在 `case.json` 中有对应 `dataset_refs`；反之 owner_cases 与用例侧 `dataset_refs` **双向一致**。
- 加载幂等、可清理、实测通过（附验证证据）。
- `suitable_for` 与所支撑验证条件的 kind 一致（边界数据不能标 normal）——它是 `case-instantiate` 逐条件配对的**匹配键**。
- 数据文件**不含真实用户凭证/PII**（测试专用数据或环境变量）。

## 检查清单

- [ ] 已按 JSON 单轨写入分片文件
- [ ] 每个 TD 六字段齐全（purpose / suitable_for / preconditions / owner_cases / load_entry / data_scope）
- [ ] `owner_cases` 与用例侧 `dataset_refs` **双向一致**
- [ ] `suitable_for` 与所支撑验证条件的 kind 一致
- [ ] 加载脚本**实测通过**，`verified` 记录（command/result/at）已写入注册表
- [ ] 加载幂等、可清理（二次执行无残留）
- [ ] 数据不含真实用户凭证/PII
- [ ] 未写入 `expected`（黑盒红线）

## 触发与边界

**该用**：用例定稿后、执行计划生成前，批量产出数据单元。

**不该用**：
- 设计用例 → `case-design`；执行 → `case-running`
- 决定"本次跑哪些配对" → 实例化（`case-instantiate` 生成、test-manager 审定）
- 单测造数（开发者自己的 fixture）→ 开发职责，不经本技能

## 常见错误

- 把 expected 写进 description（红线——预期属执行计划）。
- `suitable_for` 用 normal/boundary/negative 之外的值，或值与数据实际支撑的 kind 不符（配对匹配失效）。
- owner_cases 与用例侧 `dataset_refs` 不一致（关联断裂）。
- 加载脚本不幂等（第二次执行残留脏数据 → 后续 EXEC 全部失真）。
- 数据未实测加载就登记（违背证据先于结论）。
- 一份数据被新用例引用却未更新 owner_cases（影响面失明）。
