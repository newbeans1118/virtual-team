#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""virtual-team 运行时产物结构校验（仅用标准库）。

用法：
    python scripts/verify_artifacts.py <项目根目录>

校验范围（rules/storage-track.md 两轨）：
    JSON 轨   test/STORE-CONFIG.json、docs/prd/**/trace/prd.json、
              test/trace/*/{case,TD-REGISTRY}.json（组件/模块分层，模块层可省）、
              test/runs/RUN-*.json、RUN-*/**/EXEC-PLAN.json、RUN-*/**/EXEC.jsonl、
              test/bugs/BUG-*.json
    SQLite 轨 test/trace/metrics.db（七表存在、execs 只追加触发器、td_biz_* 孤儿检查、
              closed/verify_pass 缺陷须 verification.result=pass）
    通用      docs/prd/*/prd*.md 的需求状态（draft/gated/closed）与占位符闭合：
              closed 须零占位、gated 须占位与 §7.3 回填清单双向一致

原则：schema 未覆盖的跨产物闭合（plan_ref 回指、fail 必有 defect_ref、blocked 必有
evidence、exec_id 全局唯一）由本脚本代码检查。以 `_` 开头的键（模板说明字段）一律忽略。

退出码：0 = 全部通过；1 = 存在失败项。
"""
from __future__ import annotations

import glob
import json
import os
import re
import sqlite3
import sys

FAILURES = []
PASSES = []
SKIPS = []
# `_` 前缀键 = 模板说明字段，机制不消费，校验时忽略
IGNORE_KEY = re.compile(r"^_")


def rel(root, path):
    return os.path.relpath(path, root).replace(os.sep, "/")


def fail(rule, location, detail):
    FAILURES.append((rule, location, detail))


def ok(rule, detail):
    PASSES.append((rule, detail))


def skip(rule, detail):
    SKIPS.append((rule, detail))


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


# ------------------------------------------------- 最小 JSON Schema 校验器
def schema_validate(instance, schema, path):
    """支持子集：type / enum / pattern / required / properties /
    additionalProperties(false) / items / minItems / minimum / minLength。
    `_` 前缀键跳过（模板注释字段）。"""
    errs = []
    if isinstance(instance, dict):
        declared = schema.get("properties", {})
        for key, value in instance.items():
            if IGNORE_KEY.match(key):
                continue
            if key in declared:
                errs += schema_validate(value, declared[key], "%s.%s" % (path, key))
            elif schema.get("additionalProperties") is False:
                errs.append("%s: 禁止的额外字段 %r" % (path, key))
        for req in schema.get("required", []):
            if req not in instance:
                errs.append("%s: 缺必填字段 %r" % (path, req))
        return errs

    stype = schema.get("type")
    if stype:
        types = stype if isinstance(stype, list) else [stype]
        matched = False
        for t in types:
            if t == "object":
                matched = matched or isinstance(instance, dict)
            elif t == "array":
                matched = matched or isinstance(instance, list)
            elif t == "string":
                matched = matched or isinstance(instance, str)
            elif t == "integer":
                matched = matched or (isinstance(instance, int) and not isinstance(instance, bool))
            elif t == "number":
                matched = matched or isinstance(instance, (int, float))
            elif t == "boolean":
                matched = matched or isinstance(instance, bool)
            elif t == "null":
                matched = matched or instance is None
        if not matched:
            return ["%s: 类型应为 %s，实际 %s" % (path, stype, type(instance).__name__)]

    if "enum" in schema and instance not in schema["enum"]:
        errs.append("%s: %r 不在值域 %s" % (path, instance, schema["enum"]))
    if isinstance(instance, str):
        pat = schema.get("pattern")
        if pat and not re.search(pat, instance):
            errs.append("%s: %r 不匹配 %s" % (path, instance[:60], pat))
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errs.append("%s: 长度 < %d" % (path, schema["minLength"]))
    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errs.append("%s: 元素数 < %d" % (path, schema["minItems"]))
        if "items" in schema:
            for idx, item in enumerate(instance):
                errs += schema_validate(item, schema["items"], "%s[%d]" % (path, idx))
    if isinstance(instance, int) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            errs.append("%s: %d < minimum %d" % (path, instance, schema["minimum"]))
    return errs


def check_file(root, path, schema, rule):
    try:
        data = load_json(path)
    except Exception as exc:  # noqa: BLE001
        fail(rule, rel(root, path), "JSON 解析失败: %s" % exc)
        return None
    errs = schema_validate(data, schema, rel(root, path))
    if errs:
        for e in errs[:10]:
            fail(rule, rel(root, path), e)
        return None
    return data


def rglob(root, pattern):
    return sorted(glob.glob(os.path.join(root, pattern), recursive=True))


# ----------------------------------------------------------------- JSON 轨
def run_json_track(root, schemas):
    # 1) STORE-CONFIG（缺失 = FAIL，fail-closed，storage-track §0）
    cfg_path = os.path.join(root, "test", "STORE-CONFIG.json")
    if not os.path.exists(cfg_path):
        fail("store-config", "test/STORE-CONFIG.json", "存储轨道配置缺失（立项未完成存储决策，不得默认选轨）")
        return None
    cfg = check_file(root, cfg_path, schemas["store-config"], "store-config")
    if cfg is None:
        return None
    ok("store-config", "store=%s（%s）" % (cfg["store"], cfg.get("project", "?")))

    # 2) PRD 侧结构化分片（模块层可省略：*/trace/ 或 */*/trace/）
    prd_files = rglob(root, "docs/prd/*/*/trace/prd.json") + rglob(root, "docs/prd/*/*/*/trace/prd.json")
    check_group(root, prd_files, schemas["prd-structure"], "prd-json", "PRD 分片")

    # 3) 用例分片（模块层可省略：trace/<组件>/ 或 trace/<组件>/<模块>/）
    case_files = rglob(root, "test/trace/*/case.json") + rglob(root, "test/trace/*/*/case.json")
    check_group(root, case_files, schemas["case-structure"], "case-json", "用例分片")

    # 4) TD 注册表分片（同上，模块层可省略）
    td_files = rglob(root, "test/trace/*/TD-REGISTRY.json") + rglob(root, "test/trace/*/*/TD-REGISTRY.json")
    check_group(root, td_files, schemas["td-registry"], "td-json", "TD 注册表分片")

    # 5) RUN 头
    run_files = rglob(root, "test/runs/RUN-*.json")
    check_group(root, run_files, schemas["run"], "run-json", "RUN 头")

    # 6) EXEC-PLAN + EXEC + BUG（含跨产物闭合检查）
    exec_ids, exec_data = check_execs(root, schemas)
    check_bugs(root, schemas, exec_ids)

    # 7) 引用闭合：EXEC.plan_ref ∈ EXEC-PLAN.plan_ids（同 RUN 目录内）
    plan_files = (rglob(root, "test/runs/RUN-*/EXEC-PLAN.json")
                  + rglob(root, "test/runs/RUN-*/*/EXEC-PLAN.json")
                  + rglob(root, "test/runs/RUN-*/*/*/EXEC-PLAN.json"))
    plan_ids = set()
    for path in plan_files:
        try:
            data = load_json(path)
        except Exception:  # noqa: BLE001
            continue
        for item in data.get("items", []):
            pid = item.get("plan_id")
            if pid:
                plan_ids.add(pid)
    dangling = sorted({e["plan_ref"] for e in exec_data if e.get("plan_ref") not in plan_ids})
    if dangling:
        for ref in dangling[:10]:
            fail("exec-closure", rel(root, "test/runs"), "EXEC.plan_ref=%s 无对应 EXEC-PLAN 行" % ref)
    elif exec_data:
        ok("exec-closure", "%d 条 EXEC 的 plan_ref 全部回指 EXEC-PLAN" % len(exec_data))


def check_group(root, paths, schema, rule, label):
    if not paths:
        skip(rule, "未发现%s（阶段未到即 SKIP，非失败）" % label)
        return
    bad = 0
    for path in paths:
        if check_file(root, path, schema, rule) is None:
            bad += 1
    if bad == 0:
        ok(rule, "%d 个%s全部合规" % (len(paths), label))


def check_execs(root, schemas):
    # EXEC 明细：RUN-*/[组件/[模块/]]EXEC.jsonl（模块层、甚至组件层都可省略）
    files = (rglob(root, "test/runs/RUN-*/EXEC.jsonl")
             + rglob(root, "test/runs/RUN-*/*/EXEC.jsonl")
             + rglob(root, "test/runs/RUN-*/*/*/EXEC.jsonl"))
    exec_ids, rows = [], []
    if not files:
        skip("exec-jsonl", "未发现 EXEC 明细（阶段未到即 SKIP，非失败）")
        return exec_ids, rows
    seen = {}
    for path in files:
        try:
            with open(path, encoding="utf-8") as fh:
                lines = [ln for ln in fh.read().splitlines() if ln.strip()]
        except OSError as exc:
            fail("exec-jsonl", rel(root, path), "读取失败: %s" % exc)
            continue
        for lineno, line in enumerate(lines, 1):
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                fail("exec-jsonl", "%s:%d" % (rel(root, path), lineno), "JSONL 行解析失败: %s" % exc)
                continue
            errs = schema_validate(row, schemas["exec-line"], "%s:L%d" % (rel(root, path), lineno))
            if errs:
                for e in errs[:10]:
                    fail("exec-jsonl", "%s:L%d" % (rel(root, path), lineno), e)
                continue
            # 代码检查 1：同文件 exec_id 重复 = 追加式红线嫌疑
            key = (row["exec_id"],)
            if key in seen:
                fail("exec-jsonl", "%s:L%d" % (rel(root, path), lineno),
                     "exec_id=%s 重复（首次见 %s）——追加式红线" % (row["exec_id"], seen[key]))
            else:
                seen[key] = "L%d" % lineno
            # 代码检查 2：fail 必有 defect_ref；pass/blocked 禁止 defect_ref；
            #             blocked 必有 evidence（case-running §3）
            if row["result"] == "fail" and not row.get("defect_ref"):
                fail("exec-jsonl", "%s:L%d" % (rel(root, path), lineno), "result=fail 但缺 defect_ref（修复率分母丢失）")
            if row["result"] in ("pass", "blocked") and row.get("defect_ref"):
                fail("exec-jsonl", "%s:L%d" % (rel(root, path), lineno),
                     "result=%s 却带 defect_ref=%s" % (row["result"], row["defect_ref"]))
            if row["result"] == "blocked" and not row.get("evidence"):
                fail("exec-jsonl", "%s:L%d" % (rel(root, path), lineno), "result=blocked 但缺 evidence（阻塞原因必记）")
            exec_ids.append(row["exec_id"])
            rows.append(row)
    if not any(f[0] == "exec-jsonl" for f in FAILURES):
        ok("exec-jsonl", "%d 条 EXEC 明细合规（fail→BUG 回指 / blocked→evidence / id 全局唯一）" % len(rows))
    return exec_ids, rows


def check_bugs(root, schemas, exec_ids):
    files = rglob(root, "test/bugs/BUG-*.json")
    if not files:
        skip("bug-json", "未发现缺陷单（阶段未到即 SKIP，非失败）")
        return
    id_set = set(exec_ids)
    bad = 0
    for path in files:
        data = check_file(root, path, schemas["bug"], "bug-json")
        if data is None:
            bad += 1
            continue
        # 代码检查：source.exec 闭合（EXEC 已存在时）
        src_exec = (data.get("source") or {}).get("exec")
        if id_set and src_exec and src_exec not in id_set:
            fail("bug-closure", rel(root, path), "source.exec=%s 无对应 EXEC 行" % src_exec)
        # 代码检查：P0/P1 进入 verify_pass/closed 前须修复评审 pass（charter §6）
        sev = data.get("severity")
        status = data.get("status")
        if sev in ("P0", "P1") and status in ("verify_pass", "closed"):
            review = ((data.get("fix") or {}).get("review") or {}).get("result")
            if review != "pass":
                fail("bug-json", rel(root, path),
                     "P0/P1 到达 %s 但 fix.review.result=%r（须 pass）" % (status, review))
        # 代码检查：verify_pass/closed 须验证证据
        if status in ("verify_pass", "closed"):
            verif = data.get("verification") or {}
            if verif.get("result") != "pass":
                fail("bug-json", rel(root, path), "状态 %s 但 verification.result=%r（verify_pass 才能关闭）" % (status, verif.get("result")))
    if bad == 0 and not any(f[0] in ("bug-json", "bug-closure") for f in FAILURES):
        ok("bug-json", "%d 个缺陷单合规（评审/验证门禁闭合）" % len(files))


# --------------------------------------------------------------- SQLite 轨
MECH_TABLES = ["prd_functions", "cases", "td_registry", "runs", "exec_plans", "execs", "bugs"]


def run_sqlite_track(root, db_path):
    if not os.path.exists(db_path):
        fail("sqlite", rel(root, db_path), "metrics.db 不存在（store=sqlite 但未建库）")
        return
    con = sqlite3.connect("file:%s?mode=ro" % db_path.replace("\\", "/"), uri=True)
    try:
        cur = con.cursor()
        names = {r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        missing = [t for t in MECH_TABLES if t not in names]
        if missing:
            fail("sqlite", rel(root, db_path), "缺机制表: %s" % ", ".join(missing))
        else:
            ok("sqlite", "机制七表齐全")

        trig = {r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='trigger'")}
        need = {"trg_execs_no_update", "trg_execs_no_delete"}
        if not need <= trig:
            fail("sqlite", rel(root, db_path), "execs 只追加触发器缺失: %s" % sorted(need - trig))
        else:
            ok("sqlite", "execs 只追加触发器在位（UPDATE/DELETE → ABORT）")

        # td_biz_* 孤儿检查（storage-track：无 td_id 关联 = P0）
        biz_tables = sorted(t for t in names if t.startswith("td_biz_"))
        orphans = 0
        for table in biz_tables:
            cols = {r[1] for r in cur.execute("PRAGMA table_info(%s)" % table)}
            if "td_id" not in cols:
                fail("sqlite", table, "业务表缺 td_id 列（违反外键红线）")
                continue
            n = cur.execute(
                "SELECT COUNT(*) FROM %s WHERE td_id IS NULL OR td_id NOT IN (SELECT id FROM td_registry)" % table
            ).fetchone()[0]
            if n:
                fail("sqlite", table, "%d 行 td_id 孤儿（无注册表关联 = P0）" % n)
                orphans += n
        if biz_tables and orphans == 0 and not any(f[0] == "sqlite" for f in FAILURES):
            ok("sqlite", "%d 张业务表 td_id 外键闭合" % len(biz_tables))
        if not biz_tables:
            skip("sqlite", "尚无 td_biz_* 业务表")

        # verify_pass/closed 须验证证据（与 JSON 轨同门禁）
        n_bad = cur.execute(
            "SELECT COUNT(*) FROM bugs WHERE status IN ('verify_pass','closed') "
            "AND (verification IS NULL OR json_extract(verification,'$.result') != 'pass')"
        ).fetchone()[0]
        if n_bad:
            fail("sqlite", "bugs", "%d 个 %s 状态缺陷无 verification.result=pass 证据" % (n_bad, "verify_pass/closed"))
        # P0/P1 修复评审门禁
        n_rev = cur.execute(
            "SELECT COUNT(*) FROM bugs WHERE severity IN ('P0','P1') AND status IN ('verify_pass','closed') "
            "AND (fix IS NULL OR json_extract(fix,'$.review.result') != 'pass')"
        ).fetchone()[0]
        if n_rev:
            fail("sqlite", "bugs", "%d 个 P0/P1 到达 verify_pass/closed 但修复评审非 pass" % n_rev)
        n_total = cur.execute("SELECT COUNT(*) FROM bugs").fetchone()[0]
        if n_total and not any(f[1] == "bugs" for f in FAILURES):
            ok("sqlite", "%d 个缺陷单门禁闭合（验证 + 修复评审）" % n_total)
    finally:
        con.close()


# ------------------------------------------- PRD 需求状态与占位符闭合（skills/prd）
STATE_WORDS = ("draft", "gated", "closed")
OCC_RE = re.compile(r"【占位[^】]*】")
SEC73_RE = re.compile(r"^###\s*7\.3[^\n]*\n(.*?)(?=^###\s|^##\s|\Z)", re.S | re.M)


def _norm(text):
    return re.sub(r"\s+", "", text)


def check_prd_status(root):
    """两级完成态：gated 允许占位未清零但须全部登记；closed 须清零。

    - 未标状态 / 状态行含多个值 → FAIL
    - closed → 正文占位符必须为 0，§7.3 不得残留登记
    - gated  → 正文占位符与 §7.3 登记表双向一致（未登记 / 幽灵登记均 FAIL）
    """
    files = rglob(root, "docs/prd/*/prd*.md") + rglob(root, "docs/prd/*/*/prd*.md")
    if not files:
        skip("prd-status", "未发现组件/模块 PRD（阶段未到即 SKIP，非失败）")
        return
    bad, checked = 0, 0
    for path in files:
        try:
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
        except OSError as exc:
            fail("prd-status", rel(root, path), "读取失败: %s" % exc)
            bad += 1
            continue
        line = next((ln for ln in text.splitlines() if "需求状态" in ln), "")
        found = [w for w in STATE_WORDS if re.search(r"(?<![a-z])%s(?![a-z])" % w, line)]
        if len(found) != 1:
            fail("prd-status", rel(root, path),
                 "需求状态行须且仅须标注一个值（draft/gated/closed）；当前命中：%s" % ("、".join(found) or "无"))
            bad += 1
            continue
        state = found[0]
        checked += 1
        sec = SEC73_RE.search(text)
        body = (text[:sec.start()] + text[sec.end():]) if sec else text
        body_set = {_norm(x) for x in OCC_RE.findall(body)}
        reg_set = {_norm(x) for x in OCC_RE.findall(sec.group(1))} if sec else set()
        if state == "closed":
            if body_set:
                fail("prd-status", rel(root, path),
                     "closed 但正文仍有 %d 处占位符：%s" % (len(body_set), "、".join(sorted(body_set)[:3])))
                bad += 1
            if reg_set:
                fail("prd-status", rel(root, path), "closed 但 §7.3 仍有 %d 条待回填记录" % len(reg_set))
                bad += 1
            continue
        missing = body_set - reg_set
        ghost = reg_set - body_set
        if missing:
            fail("prd-status", rel(root, path),
                 "%d 处占位符未登记进 §7.3：%s" % (len(missing), "、".join(sorted(missing)[:3])))
            bad += 1
        if ghost:
            fail("prd-status", rel(root, path),
                 "§7.3 有 %d 条幽灵登记（正文中不存在）：%s" % (len(ghost), "、".join(sorted(ghost)[:3])))
            bad += 1
    if bad == 0 and checked:
        ok("prd-status", "%d 份 PRD 的需求状态与占位符登记闭合" % checked)


# ------------------------------------------------------------------- main
def main():
    if len(sys.argv) != 2:
        print("用法: python scripts/verify_artifacts.py <项目根目录>")
        return 2
    root = os.path.abspath(sys.argv[1])
    if not os.path.isdir(root):
        print("[FAIL] 参数 项目根目录不存在: %s" % root)
        return 2

    here = os.path.dirname(os.path.abspath(__file__))
    schema_dir = os.path.join(os.path.dirname(here), "schemas")
    rules = {
        "store-config": "store-config.schema.json",
        "prd-structure": "prd-structure.schema.json",
        "case-structure": "case-structure.schema.json",
        "td-registry": "td-registry.schema.json",
        "run": "run.schema.json",
        "exec-plan": "exec-plan.schema.json",
        "exec-line": "exec-line.schema.json",
        "bug": "bug.schema.json",
    }
    schemas = {}
    for name, fname in rules.items():
        schemas[name] = load_json(os.path.join(schema_dir, fname))

    cfg_path = os.path.join(root, "test", "STORE-CONFIG.json")
    track = None
    if os.path.exists(cfg_path):
        try:
            track = load_json(cfg_path).get("store")
        except Exception:  # noqa: BLE001
            track = None

    run_json_track(root, schemas)
    check_prd_status(root)
    if track == "sqlite":
        run_sqlite_track(root, os.path.join(root, "test", "trace", "metrics.db"))

    for rule, detail in PASSES:
        print("[PASS] %-14s %s" % (rule, detail))
    for rule, detail in SKIPS:
        print("[SKIP] %-14s %s" % (rule, detail))
    if FAILURES:
        print("")
        for rule, location, detail in FAILURES:
            print("[FAIL] %-14s %s | %s" % (rule, location, detail))
        print("\n结果：%d 项通过，%d 项跳过，%d 处失败" % (len(PASSES), len(SKIPS), len(FAILURES)))
        return 1
    print("\n结果：全部通过（%d 项检查，%d 项跳过）" % (len(PASSES), len(SKIPS)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
