---
name: case-design
description: 制定测试方案、设计功能测试用例时使用。触发场景：需要确定测试范围与准入准出标准、设计功能测试用例、生成与功能点关联的测试用例、建立覆盖率矩阵、产出 test/plan.md、提到测试方案、测试用例设计、用例覆盖。NFR 测试走独立轨 nfr-testing。
---

# 测试用例设计（case-design）

## 目的

制定测试方案，设计与功能点编号对应的测试用例，保证覆盖率。

## 执行者

`test-manager`（方案）/ `test-engineer`（用例）

## 输入

- `docs/prd/`（功能点清单，按组件/模块分层）
- `design/`
- `test/plan.md`（若已存在则增量补充）
- `test/trace/$COMPONENT/case-$MODULE.json`（结构化分片，如已存在）

## 输出（按组件/模块分片）

**分片规则**：用例设计**按组件/模块分片**——一个 test-engineer 实例只负责一个 `$COMPONENT/$MODULE`，只产出本分片用例与结构化分片；多实例并行零交叉。

- `test/plan.md`（测试方案）
- `test/cases/$COMPONENT/CASE-$COMPONENT-NNN.md`（本组件测试用例）
- 本分片 `test/trace/$COMPONENT/case-$MODULE.json`（经 case-structure）

## 测试方案内容

1. 测试范围：覆盖哪些模块与功能编号；明确不测项及原因。
2. 功能测试策略：路径覆盖（正常/边界/异常）、数据驱动。
3. 非功能测试：**不在本方案展开**——由独立 NFR 轨（`skills/nfr-testing`）负责，方案见 `test/nfr/plan-nfr.md`；本方案只声明"NFR 见独立方案"。
4. 环境与基线要求：**环境基线（baseline）定义**——测试版构建产物的干净部署态 + 本项目声明的初始化脚本/种子数据（输出到 `test/baseline/`：初始化脚本、种子数据文件、恢复方式说明）。基线是**部署级初始态**（TE 搭环境时执行），与 **TD（用例级数据）** 边界：TD 在基线之上按用例加载/清理，TD 清理后恢复到基线态。
5. 准入/准出标准。

## 用例格式（统一，`CASE-$COMPONENT-NNN` 必须与 `fr-$COMPONENT-$MODULE-NNN` 关联）

用例是**静态资产**：步骤用 `${var}` 占位符引用数据（由数据单元提供），**不写死具体数据值**；执行结果（实际结果/结论/缺陷）由 `case-running` 落在 EXEC/BUG，**不回写用例**。

```
CASE-workbench-001
关联功能点: fr-workbench-task_list-001
覆盖验证条件: fr-workbench-task_list-001:c1, fr-workbench-task_list-001:c2（引用 PRD 侧 acceptance 的 key，只引标识不复制文本）
关联数据单元: TD-workbench-003（设计意图，最终以 case-structure 的 dataset_refs 为准）
类型: 功能 | 优先级: P1
前置条件: ...
操作步骤:
  1. 加载数据单元 TD-workbench-003（执行其 load_entry）
  2. 以 ${var_a} 执行被测操作
  3. 校验返回满足 ${expected_semantics}
预期语义: ...（描述"应验证什么"，具体 expected 在执行实例行落定）
```

## 覆盖要求

- **所有功能点都必须至少有一条对应用例**（含正常路径 + 关键边界 + 异常路径）。
- **默认逐条覆盖功能点的全部 `acceptance` 条件**：每条验证条件（`{fr-id}:{key}`）都应有 ≥1 条用例覆盖；用例须在「覆盖验证条件」处声明所覆盖的 key。
- **例外出口**：某条件本轮确不覆盖时，须**显式说明理由**（如"需特定硬件环境""本轮范围外"），交 `test-manager` 判断——**不说明理由的漏覆盖 = 缺陷**。
- 覆盖缺口由 `test-rebuild` 派生为缺口报告（度量级，非门禁；是否阻塞由 test-manager 判断）。
- 设计用例时**同步识别数据需求**——按所引验证条件的 kind 识别（normal 条件需正常底座、boundary 需临界数据、negative 需非法输入），为 `test-data-gen` 提供输入；TD 的 `suitable_for` 与 kind 同枚举，是后续配对的匹配键。
- 覆盖率矩阵**不由本技能手写**——由 `test-rebuild` 从结构化数据派生（单一真相）。

## 检查清单

- [ ] 测试方案通过用户确认
- [ ] 环境基线已定义（初始化脚本/种子数据/恢复方式，产出到 `test/baseline/`）
- [ ] 全部功能点被用例覆盖
- [ ] **全部 acceptance 条件逐条覆盖**；未覆盖项已显式说明理由（交 test-manager 判断）
- [ ] 用例格式统一、编号规范、步骤参数化
- [ ] 每条用例已标注「覆盖验证条件」（引用 key，不复制文本）
- [ ] 每条用例已标注数据需求（供 test-data-gen 生成）

## 触发与边界

**该用**：测试准备阶段，出方案与用例。

**不该用**：
- 实例化（建 RUN / 配对生成实例）→ 用 `case-instantiate`
- 执行实例 → 用 `case-running`
- 结构化存储与关联 → 用 `case-structure`
- 评估测试结果 → 由 test-manager 直接评估

## 常见错误

- 用例与功能点不关联（无法证明覆盖）。
- 只写正常路径，漏边界与异常。
- **不核对功能点的 acceptance 条件**（功能点级"有用例"≠ 条件级覆盖，漏条件不可见）。
- 在用例里复制 acceptance 文本（应只引 `{fr-id}:{key}` 标识）。
- 步骤写死具体数据值（无法参数化、无法多数据集复用）。
- 在用例里填执行结果（结果属 EXEC，用例是静态资产）。
- 测试范围不写"不测项及原因"。
