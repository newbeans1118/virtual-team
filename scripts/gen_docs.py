#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 JSON 单轨派生人读文档（RTM / 测试度量 / 测试报告骨架 / NFR 报告骨架）。

设计原则
--------
1. **只派生，不创作**：所有数字来自 JSON 原始记录（prd.json / case.json / RUN / EXEC-PLAN /
   EXEC.jsonl / BUG / NFR-RUN），本脚本不做任何猜测；无法从记录得出的指标一律标注「不可得」，
   不填 0、不估算。判断类内容（测试结论、是否转缺陷、遗留建议）留占位，由责任角色填写。
2. **纯派生文档每次覆盖**（RTM / 测试度量）：手改必然与源不一致，改了就丢；`--check` 会报陈旧。
3. **含判断的文档只生成骨架**（RPT / NFR-RPT）：已存在则跳过，避免覆盖人工结论；`--force` 才重写。
4. **零依赖、可复现**：只用标准库，不写时间戳（同类输入必得同类输出），便于 `--check` 比对。

用法
----
    python scripts/gen_docs.py --root <项目根> --type rtm|metrics|report|nfr|all [选项]

选项
    --run RUN-xxx   指定执行轮（默认取编号最大的 RUN）
    --nfr-run NFR-RUN-xxx   指定 NFR 轮（默认取编号最大）
    --check         不落盘，比对现有文件；不一致（手改/源已变）→ 退出码 1
    --force         覆盖已存在的骨架类文档（RPT / NFR-RPT）
    --quiet         只报错误

产物
    docs/prd/RTM.md                          纯派生
    test/report/test-metrics-<RUN>.md        纯派生
    test/report/RPT-<RUN>.md                 骨架（存在即跳过）
    test/nfr/report/NFR-RPT-<NFR-RUN>.md     骨架（存在即跳过）

退出码
    0 成功 / 1 数据不足或 --check 发现陈旧 / 2 参数错误
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GEN_LINE = "> 本文件由 `scripts/gen_docs.py` 生成，**禁止手工编辑**；数字全部可从 JSON 原始记录复算。"


# ---------------------------------------------------------------- 基础工具

def rj(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def rjl(path):
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def find(root, pattern):
    return sorted(glob.glob(os.path.join(root, pattern), recursive=True))


def rel(root, path):
    return os.path.relpath(path, root).replace(os.sep, "/")


def project_name(root):
    cfg = os.path.join(root, "test", "STORE-CONFIG.json")
    if os.path.exists(cfg):
        try:
            name = rj(cfg).get("project")
            if name:
                return name
        except Exception:  # noqa: BLE001
            pass
    return os.path.basename(os.path.abspath(root)) or "project"


def pct(num, den):
    if not den:
        return "—"
    return "%.1f%% (%d/%d)" % (100.0 * num / den, num, den)


def write(root, rel_path, text, check, force, skeleton=False):
    """落盘或比对。返回 (状态, 说明)。skeleton=True 时已存在则跳过。"""
    target = os.path.join(root, rel_path)
    exists = os.path.exists(target)
    if check:
        if not exists:
            return "MISSING", rel_path
        if skeleton:
            return "OK", rel_path  # 骨架类含人工填写内容，只校验存在，不比对字面
        old = open(target, encoding="utf-8").read()
        return ("OK" if old == text else "STALE"), rel_path
    if skeleton and exists and not force:
        return "KEPT", rel_path
    os.makedirs(os.path.dirname(target) or ".", exist_ok=True)
    with open(target, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    return "WROTE", rel_path


# ---------------------------------------------------------------- 数据装载

def load_prd(root):
    """返回功能点列表（含组件/模块/验收条件）。"""
    funcs = []
    for path in find(root, "docs/prd/**/trace/prd.json"):
        data = rj(path)
        comp = data.get("component", "")
        mod = data.get("module", "")
        for fn in data.get("functions", []):
            funcs.append({
                "id": fn["id"],
                "name": fn.get("name", ""),
                "component": comp,
                "module": mod,
                "biz_refs": fn.get("biz_refs") or [],
                "priority": fn.get("priority", ""),
                "status": fn.get("status", "active"),
                "acceptance": fn.get("acceptance") or [],
                "source": rel(root, path),
            })
    funcs.sort(key=lambda f: (f["component"], f["module"], f["id"]))
    return funcs


def load_cases(root):
    cases = []
    for path in find(root, "test/trace/**/case.json"):
        data = rj(path)
        for c in data.get("cases", []):
            cases.append({
                "id": c["id"],
                "title": c.get("title", ""),
                "component": data.get("component", ""),
                "module": data.get("module", ""),
                "function_refs": c.get("function_refs") or [],
                "acceptance_refs": c.get("acceptance_refs") or [],
                "type": c.get("type", ""),
                "priority": c.get("priority", ""),
                "status": c.get("status", ""),
                "automatable": bool((c.get("automation") or {}).get("automatable")),
                "source": rel(root, path),
            })
    cases.sort(key=lambda c: c["id"])
    return cases


def pick_run(root, wanted=None):
    runs = []
    for path in find(root, "test/runs/RUN-*.json"):
        data = rj(path)
        runs.append((data.get("id", ""), path, data))
    if not runs:
        return None
    runs.sort(key=lambda r: r[0])
    if wanted:
        for rid, path, data in runs:
            if rid == wanted:
                return (rid, path, data)
        return None
    return runs[-1]


def load_run_detail(root, run_id):
    plans, execs = [], []
    for path in find(root, "test/runs/%s/**/EXEC-PLAN.json" % run_id):
        data = rj(path)
        for item in data.get("items", []):
            plans.append(dict(item, _shard=rel(root, path)))
    for path in find(root, "test/runs/%s/**/EXEC.jsonl" % run_id):
        for line in rjl(path):
            execs.append(dict(line, _shard=rel(root, path)))
    return plans, execs


def load_bugs(root):
    bugs = []
    for path in find(root, "test/bugs/BUG-*.json"):
        bugs.append(rj(path))
    bugs.sort(key=lambda b: b.get("id", ""))
    return bugs


def load_nfr_run(root, wanted=None):
    runs = []
    for path in find(root, "test/nfr/runs/NFR-RUN-*.json"):
        data = rj(path)
        runs.append((data.get("run", ""), path, data))
    if not runs:
        return None
    runs.sort(key=lambda r: r[0])
    if wanted:
        for rid, path, data in runs:
            if rid == wanted:
                return (rid, path, data)
        return None
    return runs[-1]


# ---------------------------------------------------------------- 统计口径

def coverage(funcs, cases):
    """需求覆盖 / 条件覆盖 / 路径覆盖（按 kind）。"""
    active_f = [f for f in funcs if f["status"] != "deprecated"]
    active_c = [c for c in cases if c["status"] == "active"]

    covered_fr = set()
    covered_cond = set()
    for c in active_c:
        covered_fr.update(c["function_refs"])
        covered_cond.update(c["acceptance_refs"])

    total_cond, kinds = 0, {"normal": [0, 0], "boundary": [0, 0], "negative": [0, 0]}
    gaps = []
    for f in active_f:
        for a in f["acceptance"]:
            total_cond += 1
            key = "%s:%s" % (f["id"], a.get("key", ""))
            hit = key in covered_cond
            kind = a.get("kind", "normal")
            if kind in kinds:
                kinds[kind][1] += 1
                if hit:
                    kinds[kind][0] += 1
            if not hit:
                gaps.append((f["id"], a.get("key", ""), kind, a.get("then", "")))

    fr_hit = [f for f in active_f if f["id"] in covered_fr]
    orphan_cases = [c["id"] for c in active_c
                    if c["function_refs"] and not (set(c["function_refs"]) & {f["id"] for f in active_f})]
    uncovered_fr = [f["id"] for f in active_f if f["id"] not in covered_fr]

    return {
        "active_funcs": active_f,
        "active_cases": active_c,
        "func_total": len(active_f),
        "func_covered": len(fr_hit),
        "cond_total": total_cond,
        "cond_covered": total_cond - len(gaps),
        "kinds": kinds,
        "gaps": gaps,
        "uncovered_fr": uncovered_fr,
        "orphan_cases": orphan_cases,
    }


def exec_stats(plans, execs):
    planned_ids = {p["plan_id"] for p in plans if p.get("plan_id")}
    done_ids = {e["plan_ref"] for e in execs if e.get("plan_ref")}
    result = {"pass": 0, "fail": 0, "blocked": 0}
    for e in execs:
        r = e.get("result")
        if r in result:
            result[r] += 1
    return {
        "planned": len(planned_ids),
        "executed": len(done_ids),
        "lines": len(execs),
        "pass": result["pass"],
        "fail": result["fail"],
        "blocked": result["blocked"],
    }


def bug_stats(bugs):
    closed = {"verify_pass", "closed", "rejected", "deferred"}
    submitting = {"in_fix", "fixed", "verify_pass", "verify_fail"}
    by_sev = {"P0": 0, "P1": 0, "P2": 0}
    open_p01 = []
    for b in bugs:
        sev = b.get("severity", "P2")
        by_sev[sev] = by_sev.get(sev, 0) + 1
        if b.get("status") not in closed and sev in ("P0", "P1"):
            open_p01.append(b)
    fixed = sum(1 for b in bugs if b.get("status") == "verify_pass")
    submitted = sum(1 for b in bugs if b.get("status") in submitting
                    or (b.get("fix") or {}).get("commit"))
    return {"total": len(bugs), "by_sev": by_sev, "open_p01": open_p01,
            "fixed": fixed, "submitted": submitted}


# ---------------------------------------------------------------- 渲染：RTM

def compress_ids(ids):
    """CASE-order-001..004 连续编号压成区间；不连续保持逐个列举。"""
    ids = sorted(ids)
    if len(ids) < 3:
        return ", ".join(ids)
    groups = {}
    for cid in ids:
        m = re.match(r"^(.*-)(\d{3})$", cid)
        if not m:
            return ", ".join(ids)
        groups.setdefault(m.group(1), []).append(int(m.group(2)))
    parts = []
    for prefix, nums in sorted(groups.items()):
        nums.sort()
        start = prev = nums[0]
        for n in nums[1:] + [None]:
            if n is not None and n == prev + 1:
                prev = n
                continue
            parts.append("%s%03d" % (prefix, start) if start == prev
                         else "%s%03d~%03d" % (prefix, start, prev))
            if n is not None:
                start = prev = n
    return ", ".join(parts)


def design_ref(root, func):
    for mod in (func["module"], "all"):
        cand = os.path.join(root, "design", func["component"], mod, "func.md")
        if os.path.exists(cand):
            return "`%s`" % rel(root, cand)
    cand = os.path.join(root, "design", func["component"], "func.md")
    if os.path.exists(cand):
        return "`%s`" % rel(root, cand)
    return "—（未产出）"


def page_matrix(root, cases):
    """扫原型页面的 data-fr 标注，形成「页面 × FR」对账。"""
    rows = []
    for path in find(root, "pages/prototype/**/*.html"):
        try:
            html = open(path, encoding="utf-8").read()
        except OSError:
            continue
        frs = []
        for m in re.finditer(r'data-fr\s*=\s*"([^"]*)"', html):
            for token in re.split(r"[,\s]+", m.group(1).strip()):
                if token and token not in frs:
                    frs.append(token)
        rows.append((rel(root, path), frs))
    return rows


def render_rtm(root, funcs, cases):
    cov = coverage(funcs, cases)
    case_by_func = {}
    for c in cov["active_cases"]:
        for fr in c["function_refs"]:
            case_by_func.setdefault(fr, []).append(c["id"])

    out = []
    out.append("# PRD 追踪矩阵（RTM）：%s" % project_name(root))
    out.append("")
    out.append(GEN_LINE)
    out.append("")
    out.append("源：`docs/prd/**/trace/prd.json`（%d 个功能点）、`test/trace/**/case.json`（%d 条 active 用例）。"
               "重跑：`python scripts/gen_docs.py --root . --type rtm`。" % (len(funcs), len(cov["active_cases"])))
    out.append("")
    out.append("## 1. 需求 → 设计 → 用例")
    out.append("")
    out.append("| 需求编号 | 需求描述 | 优先级 | 业务承接 | 设计落点 | 测试用例 | 状态 |")
    out.append("|---|---|---|---|---|---|---|")
    for f in funcs:
        out.append("| %s | %s | %s | %s | %s | %s | %s |" % (
            f["id"], f["name"] or "—", f["priority"] or "—",
            ", ".join(f["biz_refs"]) or "—",
            design_ref(root, f),
            compress_ids(case_by_func.get(f["id"], [])) or "**无用例**",
            f["status"],
        ))
    out.append("")
    out.append("## 2. 页面 × FR 覆盖")
    out.append("")
    pages = page_matrix(root, cases)
    if not pages:
        out.append("> 未发现 `pages/prototype/**/*.html`（微项目档可免原型）。")
    else:
        out.append("页面承接关系取自 HTML 根元素的 `data-fr` 标注（`data-fr=\"fr-a-b-001,fr-a-b-002\"`）。")
        out.append("")
        out.append("| 页面 | 承接 FR | 结果 |")
        out.append("|---|---|---|")
        for page, frs in pages:
            out.append("| `%s` | %s | %s |" % (page, ", ".join(frs) or "—",
                                              "已挂" if frs else "**未挂 FR**"))
    out.append("")
    out.append("## 3. 业务 → 功能（biz ↔ fr）")
    out.append("")
    biz = {}
    for f in funcs:
        for b in f["biz_refs"]:
            biz.setdefault(b, []).append(f["id"])
    if biz:
        out.append("| 业务编号 | 覆盖功能点 |")
        out.append("|---|---|")
        for b in sorted(biz):
            out.append("| %s | %s |" % (b, ", ".join(sorted(biz[b]))))
    else:
        out.append("> 功能点未声明 `biz_refs`（业务分析未产出或未关联）。")
    out.append("")
    out.append("## 4. 覆盖校验")
    out.append("")
    out.append("| 项 | 值 |")
    out.append("|---|---|")
    out.append("| 功能点（active） | %d |" % cov["func_total"])
    out.append("| 有用例覆盖的功能点 | %s |" % pct(cov["func_covered"], cov["func_total"]))
    out.append("| 验收条件（acceptance） | %d |" % cov["cond_total"])
    out.append("| 被用例引用的条件 | %s |" % pct(cov["cond_covered"], cov["cond_total"]))
    out.append("| 页面未挂 FR | %d |" % len([p for p, f in pages if not f]))
    out.append("")
    problems = []
    if cov["uncovered_fr"]:
        problems.append("无用例的功能点 %d 个：%s" % (len(cov["uncovered_fr"]), ", ".join(cov["uncovered_fr"])))
    if cov["gaps"]:
        problems.append("未覆盖的验收条件 %d 条（见 §5）" % len(cov["gaps"]))
    if cov["orphan_cases"]:
        problems.append("悬空用例 %d 条：%s" % (len(cov["orphan_cases"]), ", ".join(cov["orphan_cases"])))
    if pages and any(not f for _, f in pages):
        problems.append("有页面未挂 FR")
    out.append("**结论**：%s" % ("通过" if not problems else "不通过 —— " + "；".join(problems)))
    out.append("")
    if cov["gaps"]:
        out.append("## 5. 未覆盖的验收条件")
        out.append("")
        out.append("| 功能点 | key | kind | then（截断） |")
        out.append("|---|---|---|---|")
        for fr, key, kind, then in cov["gaps"]:
            out.append("| %s | %s | %s | %s |" % (fr, key, kind, (then or "—").replace("|", "\\|")[:60]))
    out.append("")
    return "\n".join(out)


# ---------------------------------------------------------------- 渲染：度量

def render_metrics(root, run, plans, execs, funcs, cases, bugs):
    rid, run_data = run[0], run[2]
    cov = coverage(funcs, cases)
    st = exec_stats(plans, execs)
    bs = bug_stats(bugs)

    out = ["# 测试度量报告：%s（%s）" % (run_data.get("trigger", ""), rid), "", GEN_LINE, "",
           "源：`prd.json` / `case.json` / `test/runs/%s/**` / `test/bugs/`。重跑："
           "`python scripts/gen_docs.py --root . --type metrics --run %s`。" % (rid, rid), ""]

    out += ["## 1. 本轮概览", "", "| 项 | 值 |", "|---|---|"]
    out.append("| 执行轮 | %s（%s） |" % (rid, run_data.get("trigger", "—")))
    envs = run_data.get("envs") or []
    out.append("| 环境 | %s |" % ("；".join("%s / %s / %s" % (e.get("name"), e.get("build"), e.get("commit")) for e in envs) or "—"))
    out.append("| 计划配对数 | %d |" % st["planned"])
    out.append("| 已执行（去重 plan） | %d |" % st["executed"])
    out.append("| 通过 / 失败 / 阻塞（EXEC 行） | %d / %d / %d |" % (st["pass"], st["fail"], st["blocked"]))
    out.append("")

    out += ["## 2. 核心指标", "", "| 指标 | 公式 | 值 |", "|---|---|---|"]
    out.append("| 需求覆盖率 | 有 ≥1 active 用例的功能点 ÷ active 功能点 | %s |" % pct(cov["func_covered"], cov["func_total"]))
    out.append("| 测试点级覆盖率（度量，非门禁） | 被引用的验收条件 ÷ 全部验收条件 | %s |" % pct(cov["cond_covered"], cov["cond_total"]))
    for kind, (hit, total) in cov["kinds"].items():
        out.append("| 路径覆盖度 · %s | 该 kind 已覆盖 ÷ 该 kind 总数 | %s |" % (kind, pct(hit, total)))
    out.append("| 用例执行率 | 已执行 plan 行 ÷ 计划 plan 行 | %s |" % pct(st["executed"], st["planned"]))
    out.append("| 通过率 | pass ÷ 已执行行 | %s |" % pct(st["pass"], st["lines"]))
    out.append("| 缺陷密度 | BUG 数 ÷ 已执行行 | %s |" % (("%.2f" % (bs["total"] / st["lines"])) if st["lines"] else "—"))
    out.append("| 修复率 | verify_pass ÷ 已提交修复 | %s |" % pct(bs["fixed"], bs["submitted"]))
    out.append("| 回归通过率 | 仅 `trigger=regression` 轮有意义 | %s |" % (pct(st["pass"], st["lines"]) if run_data.get("trigger") == "regression" else "不适用（本轮 %s）" % run_data.get("trigger", "—")))
    auto = sum(1 for c in cov["active_cases"] if c["automatable"])
    out.append("| 自动化率 | automatable 用例 ÷ active 用例 | %s |" % pct(auto, len(cov["active_cases"])))
    out.append("| 重开率 | 需 BUG 状态历史，JSON 无此字段 | 不可得（人工核算） |")
    out.append("")

    out += ["## 3. 验证条件缺口", ""]
    if cov["gaps"]:
        out += ["| 功能点 | key | kind | 说明 |", "|---|---|---|---|"]
        for fr, key, kind, then in cov["gaps"]:
            out.append("| %s | %s | %s | %s |" % (fr, key, kind, (then or "—").replace("|", "\\|")[:50]))
    else:
        out.append("无缺口（全部验收条件被 active 用例引用）。")
    out.append("")

    out += ["## 4. 切片分析", ""]
    case_index = {c["id"]: c for c in cov["active_cases"]}
    slices = {}
    for e in execs:
        case = case_index.get(e.get("case"))
        if not case:
            continue
        for dim in ("component", "priority", "type"):
            key = case.get(dim) or "未标注"
            bucket = slices.setdefault((dim, key), {"pass": 0, "exec": 0})
            bucket["exec"] += 1
            if e.get("result") == "pass":
                bucket["pass"] += 1
    if slices:
        out += ["| 维度 | 切片 | 通过率 | 执行行 |", "|---|---|---|---|"]
        for (dim, key) in sorted(slices):
            b = slices[(dim, key)]
            out.append("| %s | %s | %s | %d |" % (dim, key, pct(b["pass"], b["exec"]), b["exec"]))
    else:
        out.append("> 无可切片数据（EXEC 行未关联到 active 用例）。")
    out.append("")

    out += ["## 5. 风险提示", ""]
    if bs["open_p01"]:
        out.append("- 未关闭 P0/P1 缺陷 %d 条：%s" % (
            len(bs["open_p01"]),
            "、".join("%s(%s,%s)" % (b.get("id"), b.get("severity"), b.get("status")) for b in bs["open_p01"])))
    else:
        out.append("- 无未关闭 P0/P1 缺陷。")
    if cov["gaps"]:
        out.append("- 验收条件缺口 %d 条（见 §3）。" % len(cov["gaps"]))
    out.append("")
    out.append("> 结论与放行判断由 **test-manager** 在本文件之外（审定结论 / RPT）给出——本文件只提供数字。")
    out.append("")
    return "\n".join(out)


# ---------------------------------------------------------------- 渲染：RPT 骨架

def render_report(root, run, plans, execs, bugs):
    rid, run_data = run[0], run[2]
    st = exec_stats(plans, execs)
    bs = bug_stats(bugs)
    out = ["# 测试报告（RPT-%s）" % rid, "", GEN_LINE,
           "> 数字段已自动填入；**三处 `<!-- 待填 -->` 必须由 test-engineer 补全后才算完成**（结论不得由脚本代写）。",
           "", "## 1. 概述", "", "| 项 | 内容 |", "|---|---|"]
    out.append("| 报告编号 | RPT-%s |" % rid)
    envs = run_data.get("envs") or []
    out.append("| 测试版本 | %s |" % (("；".join("%s/%s" % (e.get("build"), e.get("commit")) for e in envs)) or "—"))
    out.append("| 测试环境 | %s |" % ("、".join(e.get("name", "") for e in envs) or "—"))
    out.append("| 执行轮 | %s（%s） |" % (rid, run_data.get("trigger", "—")))
    out.append("| 度量报告 | `test/report/test-metrics-%s.md`（数字唯一来源） |" % rid)
    out.append("")
    out += ["## 2. 执行摘要", "", "- 执行：计划 %d / 已执行 %d / 通过 %d / 失败 %d / 阻塞 %d（详见 test-metrics §1）"
            % (st["planned"], st["executed"], st["pass"], st["fail"], st["blocked"]),
            "- 覆盖与缺口：见 test-metrics §2、§3", "",
            "<!-- 待填：一段话说明本轮测了什么、结论倾向 -->", ""]
    out += ["## 3. 非功能测试结果", "",
            "> NFR 独立轨，见 `test/nfr/report/NFR-RPT-*.md`；不进入本报告结论。", ""]
    out += ["## 4. 遗留问题与风险", ""]
    if bs["open_p01"]:
        out += ["| 编号 | 描述 | 严重度 | 状态 |", "|---|---|---|---|"]
        for b in bs["open_p01"]:
            out.append("| %s | %s | %s | %s |" % (b.get("id"), (b.get("title") or "").replace("|", "\\|"), b.get("severity"), b.get("status")))
    else:
        out.append("无未关闭 P0/P1（由 BUG 记录派生）。")
    out += ["", "<!-- 待填：P2 / 已知限制 / 环境风险 -->", ""]
    out += ["## 5. 测试结论", "", "- **结论**：<!-- 待填：通过 / 不通过 -->",
            "- **依据**：P0/P1 遗留（见 §4）+ 覆盖缺口（test-metrics §3）",
            "- **建议**：<!-- 待填 -->", ""]
    return "\n".join(out)


# ---------------------------------------------------------------- 渲染：NFR 骨架

def render_nfr(root, nfr):
    rid, data = nfr[0], nfr[2]
    items = data.get("items") or []
    summary = data.get("summary") or {}
    build = data.get("build") or {}
    out = ["# NFR 评估报告：%s" % rid, "", GEN_LINE,
           "> 指标表已自动填入；未达标判断与「建议转缺陷」由 test-manager 补全（NFR 为参考件，不阻塞发布）。",
           "", "## 1. 概述", "", "| 项 | 内容 |", "|---|---|"]
    out.append("| 报告编号 | NFR-RPT-%s |" % rid)
    out.append("| 测试版构建 | %s / %s |" % (build.get("artifact", "—"), build.get("commit", "—")))
    out.append("| 测试环境 | %s |" % data.get("env", "—"))
    out.append("| 轮次 | %s（%s） |" % (rid, data.get("trigger", "—")))
    out.append("")
    out += ["## 2. 指标总表", "", "| NF 编号 | 指标 | 目标 | 实测 | 结论 | 证据 |", "|---|---|---|---|---|---|"]
    for it in items:
        metric = it.get("metric") or {}
        passed = metric.get("passed")
        out.append("| %s | %s | %s %s %s | %s %s | %s | %s |" % (
            it.get("nf_ref", "—"), metric.get("name", "—"),
            metric.get("op", ""), metric.get("target", ""), metric.get("unit", ""),
            metric.get("actual", "—"), metric.get("unit", ""),
            "达标" if passed is True else ("未达标" if passed is False else "—"),
            it.get("evidence", "—")))
    out.append("")
    out += ["## 3. 未达标项", ""]
    failed = [it for it in items if (it.get("metric") or {}).get("passed") is False]
    if failed:
        out += ["| NF 编号 | 指标 | 影响面 | 风险等级 |", "|---|---|---|---|"]
        for it in failed:
            out.append("| %s | %s | <!-- 待填 --> | <!-- 待填 --> |" % (it.get("nf_ref"), (it.get("metric") or {}).get("name", "")))
    else:
        out.append("无未达标项（按 NFR-RUN `metric.passed` 判定）。")
    out += ["", "## 4. 建议转缺陷", "", "<!-- 待填：NFR 轨不直接建 BUG，交 PM 决定 -->", "",
            "## 5. 结论", "",
            "- 达标率：%s" % pct(summary.get("passed", 0), summary.get("total", len(items))),
            "- 核心 NFR 风险：<!-- 待填 -->",
            "- 声明：本报告为参考件，不影响 FR 测试结论与发布判定", ""]
    return "\n".join(out)


# ---------------------------------------------------------------- 主流程

def main(argv=None):
    ap = argparse.ArgumentParser(description="从 JSON 单轨派生人读文档")
    ap.add_argument("--root", default=".", help="项目根目录（默认当前目录）")
    ap.add_argument("--type", default="all", choices=["rtm", "metrics", "report", "nfr", "all"])
    ap.add_argument("--run", default=None, help="执行轮编号，如 RUN-001")
    ap.add_argument("--nfr-run", default=None, help="NFR 轮编号")
    ap.add_argument("--check", action="store_true", help="只比对不写入；不一致退出 1")
    ap.add_argument("--force", action="store_true", help="覆盖已存在的骨架类文档")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        sys.stderr.write("错误：项目根不存在：%s\n" % root)
        return 2

    results, errors = [], []

    def report(status, path, note=""):
        results.append((status, path, note))

    funcs = load_prd(root)
    cases = load_cases(root) if args.type in ("rtm", "metrics", "all") else []
    bugs = load_bugs(root) if args.type in ("metrics", "report", "all") else []

    if args.type in ("rtm", "all"):
        if not funcs:
            errors.append("未找到 docs/prd/**/trace/prd.json（先用 /vt-prd 产出行需求结构）")
        else:
            report(*write(root, "docs/prd/RTM.md", render_rtm(root, funcs, cases), args.check, args.force))

    if args.type in ("metrics", "report", "all"):
        run = pick_run(root, args.run)
        if run is None:
            errors.append("未找到 test/runs/RUN-*.json%s" % ("（指定 %s）" % args.run if args.run else ""))
        else:
            plans, execs = load_run_detail(root, run[0])
            if args.type in ("metrics", "all"):
                text = render_metrics(root, run, plans, execs, funcs, cases, bugs)
                report(*write(root, "test/report/test-metrics-%s.md" % run[0], text, args.check, args.force))
            if args.type in ("report", "all"):
                text = render_report(root, run, plans, execs, bugs)
                report(*write(root, "test/report/RPT-%s.md" % run[0], text, args.check, args.force, skeleton=True))

    if args.type in ("nfr", "all"):
        nfr = load_nfr_run(root, args.nfr_run)
        if nfr is None:
            if args.type == "nfr":
                errors.append("未找到 test/nfr/runs/NFR-RUN-*.json")
        else:
            text = render_nfr(root, nfr)
            report(*write(root, "test/nfr/report/NFR-RPT-%s.md" % nfr[0], text, args.check, args.force, skeleton=True))

    if not args.quiet:
        label = {"WROTE": "已生成", "KEPT": "已存在（保留人工内容）", "OK": "一致",
                 "STALE": "陈旧（源已变或手改）", "MISSING": "缺失"}
        for status, path, _ in results:
            print("[%s] %s" % (label.get(status, status), path))
        for err in errors:
            print("[跳过] %s" % err)

    if errors:
        return 1
    if args.check and any(s in ("STALE", "MISSING") for s, _, _ in results):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
