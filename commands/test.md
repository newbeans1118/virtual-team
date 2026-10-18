---
description: 测试阶段：制定测试方案、设计并执行用例、跟踪缺陷、产出测试报告
argument-hint: "测试范围，例如：全部功能点 或 user-auth 模块"
---

<user_input>
$ARGUMENTS
</user_input>

---

委派 **test-manager**（方案/评估）与 **test-engineer**（用例/执行）agent。

## 要求

1. 读取 `rules/team-charter.md`、`docs/requirements/`、`design/`、`src/`。
2. `test-manager`：
   - 用 `case-design` 产出 `test/plan.md`（范围/功能/非功能策略）
   - 生成 `test/baseline/` 基线数据
3. `test-engineer`：
   - 用 `case-design` 生成 `test/cases/CASE-xxx.md`（与功能点编号关联）
   - 用 `case-structure` 结构化用例并关联功能点与数据单元（覆盖率矩阵由 `test-rebuild` 派生）
   - 按 `release/manual-install.md` 搭建环境，用 `case-running` 执行
   - 提交缺陷 `BUG-xxx` 并跟踪修复
4. `test-manager` 评估结果，判定是否通过。

## 通过标准（硬性）

- **无 P0/P1 缺陷遗留**。
- **用例覆盖所有功能点**。

## 禁止

- test-manager **只读、不编译、不运行**代码。
- test-engineer **不得修改代码或非测试文档**。
