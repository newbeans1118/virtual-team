---
description: 测试阶段：制定测试方案、设计并执行用例、跟踪缺陷、产出测试报告
argument-hint: "测试范围，例如：全部功能点 或 workbench 组件"
---

<user_input>
$ARGUMENTS
</user_input>

---

> 派发按 charter §5 说明 2b：**经 PM 派发**；评审员无消息通道，问题一律**报 PM 中转**，不得直接发送给责任角色。

委派 **test-manager**（方案/RUN 头/评估）与 **test-engineer**（用例/数据/执行）agent。

> **NFR 不在此命令内**：非功能评估走 `/vt-nfr-test`（独立轨，仅参考报告，不阻塞本流程）。

## 前置

- **测试版构建已完成**（`release/artifact/` + `release/manual-install.md`，代码评审闭环后由 release-engineer 产出）——测试环境来源；未完成 → 先执行 `/vt-build-test`。
- 用例/TD 设计无此前置（可与编码并行，只依赖需求+设计文档）。

## 要求

1. 读取 `rules/team-charter.md`、`docs/prd/`、`design/`、`src/`。
2. `test-manager`：
   - 用 `case-design` 产出 `test/plan.md`（范围/功能/非功能策略 + **环境基线定义**）
   - 定义环境基线并产出 `test/baseline/`（初始化脚本、种子数据、恢复方式；执行由 test-engineer 搭环境时进行）
   - **建 RUN 头**（trigger/scope/envs；证据见 charter §5），连执行派发建议交 PM
3. `test-engineer`：
   - 用 `case-design` 生成 `test/cases/$COMPONENT/CASE-$COMPONENT-NNN.md`（与功能点编号关联）
   - 用 `case-structure` 结构化用例并关联功能点与数据单元（覆盖率矩阵由 `test-rebuild` 派生）；结构化后重跑 `python scripts/gen_docs.py --root . --type rtm`，让 RTM 的用例列与覆盖率齐全
   - 用 `test-data-gen` 生成 TD 并登记注册表（加载脚本在测试版构建产物上实测通过后才登记）
   - 按测试版构建产物 + `release/manual-install.md` 搭建环境（**环境必须来自测试版构建**）
   - 用 `case-instantiate` 在 TM 已建的 RUN 内配对生成**可执行实例**（交 test-manager 审定）
   - 用 `case-running` 执行已审定实例、记录 EXEC，提交缺陷 `BUG-xxx` 并跟踪修复
4. 派生本轮文档：`python scripts/gen_docs.py --root . --type metrics`（数字，禁手改）与 `--type report`（RPT 骨架，补三处待填）；`test-manager` 据此判定是否通过（轮次汇总亦由 test-rebuild 派生，数字冲突以 metrics 为准）。

## 通过标准（硬性）

- **无 P0/P1 缺陷遗留**。
- **用例覆盖所有功能点**。

## 禁止

- test-manager **只读、不编译、不运行**代码。
- test-engineer **不得修改代码或非测试文档**。
- 用开发工作区充当测试环境（违反 charter §5）。

## 档位裁剪（判据与不可裁红线见 charter §9；档位读 `board/KANBAN.md` 首行，未定档按标准档）

- **微项目**：RUN 单分片单 env、**免覆盖率矩阵**、TD 注册表只登记不审定、NFR 轨不启用。
- **标准（默认）**：按组件分片，覆盖率矩阵按需生成，TD 注册表与实例计划仍须 TM 审定。
- **完整**：多 env 并行 + 覆盖率矩阵 + 逐条件配对审定。
