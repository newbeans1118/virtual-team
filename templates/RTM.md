# RTM（PRD 追踪矩阵）——生成物

> 模版：RTM.md ｜ 生成：`python scripts/gen_docs.py --root . --type rtm` ｜ 存放：`docs/prd/RTM.md` ｜ 责任角色：product-manager（触发与回源修复）
> **本文件不是手写文档**：内容全部由 JSON 单轨与原型标注派生，重跑即覆盖。手改会被 `verify_artifacts.py` 的 `derived-docs` 规则判 **FAIL**。

## 1. 段落来源

| 段 | 内容 | 数据来源 | 谁保证源数据正确 |
|----|------|---------|-----------------|
| §1 需求 → 设计 → 用例 | 功能点 / 优先级 / 业务承接 / 设计落点 / 覆盖用例 / 状态 | `docs/prd/**/trace/prd.json`、`test/trace/**/case.json`、`design/**/func.md` 是否存在 | product-manager（prd-structure）、architect（设计）、test-engineer（case-structure） |
| §2 页面 × FR | 页面清单与承接 FR | `pages/prototype/**/*.html` 的 `data-fr` 标注（见 `skills/prototype`） | product-manager（原型） |
| §3 业务 → 功能 | `biz_refs` 反查 | `prd.json` 的 `functions[].biz_refs` | product-manager（业务分析 → PRD） |
| §4 覆盖校验 | 覆盖率、缺口、结论 | 上述数据的聚合计算 | 脚本计算，不接受人工改判 |
| §5 未覆盖条件 | 缺口明细 | `acceptance[]` 与 `case.acceptance_refs` 的差集 | 脚本计算 |

## 2. 生成时机（三处）

1. **PRD 结构化完成**后（`prd.json` 落盘）——§1/§3 有意义；
2. **用例结构化完成**后（`case.json` 落盘）——§1「测试用例」列与 §4 覆盖率才完整；
3. **原型变更**后（页面增删或 `data-fr` 改动）。

## 3. 红线

- **不得在 RTM 里补数据**：缺哪行就回源文件补（`prd.json` / `case.json` / 页面 `data-fr`），补完重跑。
- **不得手改结论**：§4 的「通过 / 不通过」由脚本按缺口算出，人工改判无效（重跑即还原）。
- 页面未挂 FR：要么补 FR，要么删元素；占位符写在原型元素上，不写进 RTM。
- 实现进度不在本表（唯一真相在 `board/KANBAN.md`）。
