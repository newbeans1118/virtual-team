---
description: 测试阶段：制定测试方案、设计并执行用例、跟踪缺陷、产出测试报告
argument-hint: "测试范围，例如：全部功能点 或 workbench 组件"
---

<user_input>
$ARGUMENTS
</user_input>

---

委派 **test-manager**（方案/RUN 头/评估）与 **test-engineer**（用例/数据/执行）agent。

## 前置

- **测试版构建已完成**（`release/artifact/` + `release/manual-install.md`，代码评审闭环后由 release-engineer 产出）——测试环境来源；未完成 → 先执行 `/build-test`。
- 用例/TD 设计无此前置（可与编码并行，只依赖需求+设计文档）。

## 要求

1. 读取 `rules/team-charter.md`、`docs/prd/`、`design/`、`src/`。
2. `test-manager`：
   - 用 `case-design` 产出 `test/plan.md`（范围/功能/非功能策略 + **环境基线定义**）
   - 定义环境基线并产出 `test/baseline/`（初始化脚本、种子数据、恢复方式；执行由 test-engineer 搭环境时进行）
   - **建 RUN 头**（trigger/scope/envs——build/commit 引用测试版构建产物），连执行派发建议交 PM
3. `test-engineer`：
   - 用 `case-design` 生成 `test/cases/$COMPONENT/CASE-$COMPONENT-NNN.md`（与功能点编号关联）
   - 用 `case-structure` 结构化用例并关联功能点与数据单元（覆盖率矩阵由 `test-rebuild` 派生）
   - 用 `test-data-gen` 生成 TD 并登记注册表（加载脚本在测试版构建产物上实测通过后才登记）
   - 按测试版构建产物 + `release/manual-install.md` 搭建环境（**环境必须来自测试版构建**）
   - 用 `case-instantiate` 在 TM 已建的 RUN 内配对生成**可执行实例**（交 test-manager 审定）
   - 用 `case-running` 执行已审定实例、记录 EXEC，提交缺陷 `BUG-xxx` 并跟踪修复
4. `test-manager` 评估结果（读 test-rebuild 度量——轮次汇总亦由其派生），判定是否通过。

## 通过标准（硬性）

- **无 P0/P1 缺陷遗留**。
- **用例覆盖所有功能点**。

## 禁止

- test-manager **只读、不编译、不运行**代码。
- test-engineer **不得修改代码或非测试文档**。
- 用开发工作区充当测试环境（必须走测试版构建产物）。
