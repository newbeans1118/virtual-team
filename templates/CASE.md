# 测试用例

> 模版：CASE.md ｜ 产出角色：test-engineer ｜ 存放：test/cases/$COMPONENT/CASE-$COMPONENT-NNN.md

## CASE-$COMPONENT-NNN （用例标题）

| 项 | 内容 |
|----|------|
| 用例编号 | CASE-$COMPONENT-NNN |
| 关联功能点 | fr-$COMPONENT-$MODULE-NNN（可多个，可跨组件/模块） |
| 覆盖验证条件 | fr-$COMPONENT-$MODULE-NNN:c1, ...:c2（引用 req 侧 acceptance 的 key；只引标识，不复制文本） |
| 用例类型 | 功能 / 性能 / 安全 / 兼容 |
| 优先级 | P0 / P1 / P2 |
| 前置条件 | |
| 测试数据 | |

### 操作步骤

1. 
2. 
3. 

### 预期结果

- 

> **用例是静态资产**：不在此记录实际结果/结论/缺陷——那些属执行明细（EXEC）与缺陷单（BUG），由 `case-running` 落地，**不回写用例**。
> 步骤与预期可与所覆盖验证条件的 GWT 对应（`when` → 步骤，`then` → 预期）。
