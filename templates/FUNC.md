# 功能设计：$PROJECT_NAME

> 产出角色：architect ｜ 存放：design/FUNC.md

## 1. 说明

以组件/模块为单位组织，每个设计条目必须关联功能编号 `fr-$COMPONENT-$MODULE-NNN`。

---

## 2. 组件/模块：$COMPONENT / $MODULE

### 2.1 fr-$COMPONENT-$MODULE-NNN （功能名称）

| 项 | 内容 |
|----|------|
| 对应功能编号 | fr-$COMPONENT-$MODULE-NNN |
| 所属组件/模块 | $COMPONENT / $MODULE |
| 功能说明 | |
| 依赖 | |
| 处理流程 | 见下方流程 |
| 异常路径 | |

```mermaid
flowchart TD
  S([入口]) --> A[校验] --> B[处理] --> C[写库] --> E([返回])
  A -- 校验失败 --> X[返回错误]
```

---

## 3. 模块交互

```mermaid
flowchart LR
  M1[模块A] --> M2[模块B]
```
