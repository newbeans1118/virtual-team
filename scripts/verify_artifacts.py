#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""virtual-team 运行时产物结构校验（仅用标准库）。

用法：
    python scripts/verify_artifacts.py <项目根目录> [--stage <阶段>]

--stage 声明当前流程阶段（kickoff/prd/design/coding/review/build-test/test/accept/release）。
声明后按 STAGE_REQUIRED 检查该阶段必需产物；未声明时若全部产物组都 SKIP（空项目）则 FAIL，
避免「什么都没做也判全部通过」。阶段未到的产物仍按 SKIP 处理，不算失败。

校验范围（rules/storage-track.md，JSON 单轨）：
    JSON 轨   test/STORE-CONFIG.json、docs/prd/**/trace/prd.json、
              test/trace/*/{case,TD-REGISTRY}.json（组件/模块分层，模块层可省）、
              test/runs/RUN-*.json、RUN-*/**/EXEC-PLAN.json、RUN-*/**/EXEC.jsonl、
              test/bugs/BUG-*.json
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


# 产物组规则：每条要么 PASS、要么 SKIP（阶段未到）。全 SKIP = 空项目。
ARTIFACT_RULES = ("prd-json", "case-json", "td-json", "run-json",
                  "exec-plan-json", "exec-jsonl", "bug-json", "prd-status")

# 各阶段必需产物（只列该阶段确实会产出、且能被本脚本机械判定的产物组）。
# 未列出的产物组允许 SKIP；release/ 下的发布证据不在此列——真实性靠人工回执，机械校验无解。
STAGE_REQUIRED = {
    "kickoff": (),
    "prd": ("prd-json",),
    "design": ("prd-json",),
    "coding": ("prd-json",),
    "review": ("prd-json",),
    "build-test": ("prd-json",),
    "test": ("case-json", "td-json", "run-json", "exec-plan-json", "exec-jsonl"),
    "accept": ("case-json", "td-json", "run-json", "exec-plan-json", "exec-jsonl"),
    "release": ("case-json", "td-json", "run-json", "exec-plan-json", "exec-jsonl"),
}


def check_stage(stage):
    """fail-closed：未声明阶段且空项目 → FAIL；声明阶段则必需产物缺一即 FAIL。"""
    passed = {r for r, _ in PASSES}
    skipped = {r for r, _ in SKIPS}
    if stage is None:
        if all(r in skipped for r in ARTIFACT_RULES):
            fail("stage", "项目根",
                 "未声明 --stage 且 %d 类产物全部缺失（空项目不得判全部通过）；"
                 "按阶段校验请传 --stage <阶段>" % len(ARTIFACT_RULES))
        else:
            produced = [r for r in ARTIFACT_RULES if r in passed]
            ok("stage", "未声明阶段，按已产物校验（%d/%d 类产物已产生）"
               % (len(produced), len(ARTIFACT_RULES)))
        return
    if stage not in STAGE_REQUIRED:
        fail("stage", "--stage=%s" % stage,
             "未知阶段，可选：%s" % ", ".join(STAGE_REQUIRED))
        return
    required = STAGE_REQUIRED[stage]
    missing = [r for r in required if r not in passed]
    if missing:
        fail("stage", "--stage=%s" % stage,
             "必需产物缺失或未通过：%s" % ", ".join(missing))
    else:
        ok("stage", "阶段=%s 的 %d 类必需产物齐备" % (stage, len(required)))


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


# ------------------------------------------------- 最小 JSON Schema 校验器
def schema_validate(instance, schema, path):
    """支持子集：type / enum / pattern / required / properties /
    additionalProperties(false) / items / minItems / minimum / minLength。
    `_` 前缀键跳过（模板注释字段）。

    注意：dict 实例同样要先过 type/enum 检查，再校验 properties/required；
    提前 return 会让「本应为 array 却写成 object」的实例蒙混过关。"""
    errs = []

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
        fail("store-config", "test/STORE-CONFIG.json", "存储配置缺失（立项时未创建 STORE-CONFIG.json，不得代为默认创建）")
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

    # 7) EXEC-PLAN：schema 校验 + 审定门禁 + plan_id 全局唯一 + plan_ref 同 RUN 回指
    plan_files = (rglob(root, "test/runs/RUN-*/EXEC-PLAN.json")
                  + rglob(root, "test/runs/RUN-*/*/EXEC-PLAN.json")
                  + rglob(root, "test/runs/RUN-*/*/*/EXEC-PLAN.json"))
    if not plan_files:
        skip("exec-plan-json", "未发现 EXEC-PLAN（阶段未到即 SKIP，非失败）")
    plan_ids_by_run = {}   # run_id -> set(plan_id)，回指只在所属 RUN 内成立
    plan_owner = {}        # plan_id -> 首次出现路径（跨 RUN 全局查重）
    bad = 0
    for path in plan_files:
        data = check_file(root, path, schemas["exec-plan"], "exec-plan-json")
        if data is None:
            bad += 1
            continue
        # 审定门禁（charter §5：实例计划未经 test-manager 审定不得执行）
        if not data.get("approved_by"):
            fail("exec-plan-json", rel(root, path),
                 "approved_by 为空（实例计划未经 test-manager 审定，不得执行）")
            bad += 1
        run_id = data.get("run", "?")
        bucket = plan_ids_by_run.setdefault(run_id, set())
        for item in data.get("items", []):
            pid = item.get("plan_id")
            if not pid:
                continue
            if pid in plan_owner:
                fail("plan-unique", rel(root, path),
                     "plan_id=%s 重复（首次见 %s）——charter §5 要求跨 RUN 全局唯一"
                     % (pid, plan_owner[pid]))
                bad += 1
            else:
                plan_owner[pid] = rel(root, path)
            bucket.add(pid)
    if plan_files and bad == 0:
        ok("exec-plan-json", "%d 个 EXEC-PLAN 合规（schema + approved_by 审定 + plan_id 全局唯一）"
           % len(plan_files))

    dangling = sorted({(e.get("run", "?"), e["plan_ref"]) for e in exec_data
                       if e.get("plan_ref") not in plan_ids_by_run.get(e.get("run", "?"), set())})
    if dangling:
        for run_id, ref in dangling[:10]:
            fail("exec-closure", rel(root, os.path.join(root, "test", "runs")),
                 "RUN=%s 的 EXEC.plan_ref=%s 在本 RUN 内无对应 EXEC-PLAN 行" % (run_id, ref))
    elif exec_data:
        ok("exec-closure", "%d 条 EXEC 的 plan_ref 在所属 RUN 内全部回指 EXEC-PLAN" % len(exec_data))


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
def check_derived(root):
    """派生文档来源检查（`derived-docs` 规则）。

    均为**内容级**逐字比对（重算后比字符串，手改或源已变即 FAIL）：
    - RTM：由 `prd.json` / `case.json` 完全决定；
    - 测试度量：由 prd / case / RUN / EXEC-PLAN / EXEC / BUG 完全决定。

    骨架类（RPT / NFR-RPT）含人工结论，不参与内容比对——只要求首部带生成声明。
    """
    generated = "由 `scripts/gen_docs.py` 生成"
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)
    try:
        import gen_docs  # 同目录脚本，仅作渲染复用
    except Exception:  # noqa: BLE001
        skip("derived-docs", "gen_docs.py 不可导入，跳过派生文档比对")
        return

    def compare(path, expected, label, hint):
        try:
            actual = open(path, encoding="utf-8").read()
        except OSError as exc:
            fail("derived-docs", label, "无法读取：%s" % exc)
            return
        if actual.strip() != expected.strip():
            fail("derived-docs", label, "与 JSON 原始记录不一致（手改或源已变）→ %s" % hint)
        else:
            ok("derived-docs", "%s（与源一致）" % label)

    funcs = gen_docs.load_prd(root)
    cases = gen_docs.load_cases(root)

    rtm = os.path.join(root, "docs", "prd", "RTM.md")
    if os.path.exists(rtm) and funcs:
        compare(rtm, gen_docs.render_rtm(root, funcs, cases),
                "docs/prd/RTM.md", "重跑 scripts/gen_docs.py --type rtm")

    bugs = gen_docs.load_bugs(root)
    for path in sorted(glob.glob(os.path.join(root, "test", "report", "test-metrics-*.md"))):
        label = os.path.relpath(path, root).replace(os.sep, "/")
        rid = os.path.basename(path)[len("test-metrics-"):-len(".md")]
        run = gen_docs.pick_run(root, rid)
        if run is None:
            fail("derived-docs", label, "对应执行轮 %s 不存在——孤儿文档，应删除" % rid)
            continue
        plans, execs = gen_docs.load_run_detail(root, rid)
        compare(path, gen_docs.render_metrics(root, run, plans, execs, funcs, cases, bugs),
                label, "重跑 scripts/gen_docs.py --type metrics --run %s" % rid)

    for path in sorted(glob.glob(os.path.join(root, "test", "report", "RPT-*.md")) +
                       glob.glob(os.path.join(root, "test", "nfr", "report", "NFR-RPT-*.md"))):
        label = os.path.relpath(path, root).replace(os.sep, "/")
        if generated not in open(path, encoding="utf-8").read(400):
            fail("derived-docs", label, "缺少生成声明——骨架须由 gen_docs.py 生成，人工只补待填段")


def main():
    usage = ("用法: python scripts/verify_artifacts.py <项目根目录> [--stage <阶段>] [--json]\n"
             "      或 python scripts/verify_artifacts.py --root <项目根目录> [--stage <阶段>] [--json]")
    args = sys.argv[1:]
    stage = None
    as_json = False
    positional = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--stage":
            if i + 1 >= len(args):
                print(usage)
                return 2
            stage = args[i + 1]
            i += 2
        elif arg.startswith("--stage="):
            stage = arg.split("=", 1)[1]
            i += 1
        elif arg == "--root":
            if i + 1 >= len(args):
                print(usage)
                return 2
            positional.append(args[i + 1])
            i += 2
        elif arg == "--json":
            as_json = True
            i += 1
        else:
            positional.append(arg)
            i += 1
    if len(positional) != 1:
        print(usage)
        return 2
    root = os.path.abspath(positional[0])
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
    check_derived(root)
    check_stage(stage)

    if as_json:
        payload = {
            "root": root,
            "stage": stage,
            "pass": [{"rule": r, "detail": d} for r, d in PASSES],
            "skip": [{"rule": r, "detail": d} for r, d in SKIPS],
            "fail": [{"rule": r, "location": loc, "detail": d} for r, loc, d in FAILURES],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=1))
        return 1 if FAILURES else 0

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
