# 测试度量报告——生成物

> 模版：TEST-METRICS.md ｜ 生成：`python scripts/gen_docs.py --root . --type metrics [--run RUN-xxx]` ｜ 存放：`test/report/test-metrics-<RUN>.md` ｜ 责任角色：test-engineer（触发）
> **数字全部由 JSON 原始记录算出，禁止手抄、禁止手改**；`--check` 与 `verify_artifacts.py` 的 `derived-docs` 会检出非生成物或被改动的文件。

## 1. 指标口径（与脚本实现一一对应）

| 指标 | 公式 | 源 |
|------|------|----|
| 需求覆盖率 | 被 ≥1 条 active 用例引用的功能点 ÷ active 功能点 | `prd.json` × `case.json` |
| 测试点级覆盖率 | 被 `acceptance_refs` 引用的条件 ÷ 全部 `acceptance[]` | `prd.json` × `case.json` |
| 路径覆盖度（按 kind） | 每个 kind 已覆盖 ÷ 该 kind 总数 | `acceptance[].kind` |
| 用例执行率 | 已执行 `plan_ref` 去重数 ÷ 计划 `plan_id` 数 | `EXEC-PLAN` × `EXEC.jsonl` |
| 通过率 | `result=pass` 行数 ÷ EXEC 行数 | `EXEC.jsonl` |
| 缺陷密度 | BUG 数 ÷ EXEC 行数 | `test/bugs/` × `EXEC.jsonl` |
| 修复率 | `verify_pass` ÷ 已提交修复（含 `fix.commit`） | `BUG.json` |
| 自动化率 | `automation.automatable=true` ÷ active 用例 | `case.json` |
| 重开率 | **不可得**：BUG 无状态历史字段，脚本明确标注而不估算 | — |

## 2. 硬约束

- **不可得的指标标「不可得」，不填 0**：0 是数据，编造的 0 是假证据。
- **结论不写在本文件**：本文件只给数字；放行判断由 test-manager 在审定结论 / RPT 中出。
- **本文件不抄门禁结论**：门禁结果只看 `verify_artifacts.py` 的实时输出；把结果抄进静态文档必然过期，是漂移源。
- `--check` 返回非 0（陈旧）时，先重跑生成再提交评审；改数字不改源 = 造假。
