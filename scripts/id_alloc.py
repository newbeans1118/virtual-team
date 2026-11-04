#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""虚拟团队编号分配器（零依赖，仅标准库）。

用法：
    python scripts/id_alloc.py <项目根> fr --component order --module all [--count 3]
    python scripts/id_alloc.py <项目根> biz --component order --module all
    python scripts/id_alloc.py <项目根> case --component order
    python scripts/id_alloc.py <项目根> td --component order
    python scripts/id_alloc.py <项目根> bug --component order
    python scripts/id_alloc.py <项目根> cr --component order
    python scripts/id_alloc.py <项目根> run
    python scripts/id_alloc.py <项目根> p [--count 5]
    python scripts/id_alloc.py <项目根> nfr-case --component pay
    python scripts/id_alloc.py <项目根> nfr-td   --component pay
    python scripts/id_alloc.py <项目根> nfr-run
    python scripts/id_alloc.py <项目根> nfr-p
    python scripts/id_alloc.py <项目根> exec --plan-ref P-003
    python scripts/id_alloc.py <项目根> check

设计要点（对齐 rules/team-charter.md §2）：
- **永不复用**：取 max(磁盘扫描最大号, 账本最大号) + 1，删产物也不回退。
- **账本防重号**：分配结果写入 <项目根>/test/trace/id-ledger.json，
  两个子代理并发分配时后者能看见前者已占用的号（不是分布式锁，
  但消除了「产物尚未落盘时重号」这个主要成因）。
- **只分配不落盘**：编号写进产物仍由责任角色完成，本工具不改业务文件。
- **check 模式**：全项目编号查重 + 格式校验，供 PM 与评审员使用。

退出码：0 正常；1 check 发现问题；2 用法/参数错误。
"""

import json
import os
import re
import sys

SKIP_DIRS = {".git", "build", "node_modules", ".workbuddy", "__pycache__", ".venv", "venv"}
TEXT_EXT = (".json", ".jsonl", ".md", ".sql", ".sh", ".txt", ".yaml", ".yml")

LEDGER_REL = os.path.join("test", "trace", "id-ledger.json")

SNAKE = re.compile(r"^[a-z][a-z0-9_]*$")


class Spec(object):
    """一种编号的分配规则。"""

    def __init__(self, key, fmt, pattern, needs_component=False, needs_module=False):
        self.key = key
        self.fmt = fmt                # 打印格式模板
        self.pattern = re.compile(pattern)   # 带命名组 n 的扫描正则
        self.needs_component = needs_component
        self.needs_module = needs_module


SPECS = {
    "biz": Spec("biz", "biz-{c}-{m}-{n:03d}",
                r"\bbiz-(?P<c>[A-Za-z0-9_]+)-(?P<m>[A-Za-z0-9_]+)-(?P<n>\d{3})\b",
                True, True),
    "fr": Spec("fr", "fr-{c}-{m}-{n:03d}",
               r"\bfr-(?P<c>[A-Za-z0-9_]+)-(?P<m>[A-Za-z0-9_]+)-(?P<n>\d{3})\b",
               True, True),
    "case": Spec("case", "CASE-{c}-{n:03d}",
                 r"\bCASE-(?P<c>[A-Za-z0-9_]+)-(?P<n>\d{3})\b", True, False),
    "td": Spec("td", "TD-{c}-{n:03d}",
               r"\bTD-(?P<c>[A-Za-z0-9_]+)-(?P<n>\d{3})\b", True, False),
    "bug": Spec("bug", "BUG-{c}-{n:03d}",
                r"\bBUG-(?P<c>[A-Za-z0-9_]+)-(?P<n>\d{3})\b", True, False),
    "cr": Spec("cr", "CR-{c}-{n:03d}",
               r"\bCR-(?P<c>[A-Za-z0-9_]+)-(?P<n>\d{3})\b", True, False),
    "run": Spec("run", "RUN-{n:03d}",
                r"\bRUN-(?P<n>\d{3})\b"),
    "p": Spec("p", "P-{n:03d}",
              r"\bP-(?P<n>\d{3})(?!-?\d)"),
    "nfr-case": Spec("nfr-case", "NFR-CASE-{c}-{n:03d}",
                     r"\bNFR-CASE-(?P<c>[A-Za-z0-9_]+)-(?P<n>\d{3})\b", True, False),
    "nfr-td": Spec("nfr-td", "NFR-TD-{c}-{n:03d}",
                   r"\bNFR-TD-(?P<c>[A-Za-z0-9_]+)-(?P<n>\d{3})\b", True, False),
    "nfr-run": Spec("nfr-run", "NFR-RUN-{n:03d}",
                    r"\bNFR-RUN-(?P<n>\d{3})\b"),
    "nfr-p": Spec("nfr-p", "NFR-P-{n:03d}",
                  r"\bNFR-P-(?P<n>\d{3})(?!-?\d)"),
}

EXEC_RE = re.compile(r"\bP-(?P<p>\d{3})-(?P<s>\d+)\b")


# ------------------------------------------------------------------ 扫描

def walk_text_files(root):
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            if name.lower().endswith(TEXT_EXT):
                yield os.path.join(base, name)


def scan(root):
    """返回 (max_by_key, all_ids)。

    max_by_key 形如 {'fr:order:all': 12, 'CASE:order': 3, 'RUN': 7, 'P': 42,
                     'EXEC:P-003': 2}
    """
    max_by_key = {}
    all_ids = []

    def bump(key, num):
        if num > max_by_key.get(key, 0):
            max_by_key[key] = num

    for path in walk_text_files(root):
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            continue
        for spec in SPECS.values():
            for m in spec.pattern.finditer(text):
                num = int(m.group("n"))
                if spec.needs_component:
                    comp = m.group("c")
                    mod = m.group("m") if spec.needs_module else None
                    key = "%s:%s" % (spec.key, comp) if mod is None else \
                          "%s:%s:%s" % (spec.key, comp, mod)
                else:
                    key = spec.key
                bump(key, num)
                all_ids.append((path, m.group(0)))
        for m in EXEC_RE.finditer(text):
            key = "EXEC:P-%s" % m.group("p")
            bump(key, int(m.group("s")))
            all_ids.append((path, m.group(0)))
    return max_by_key, all_ids


# ------------------------------------------------------------------ 账本

def load_ledger(root):
    path = os.path.join(root, LEDGER_REL)
    if not os.path.exists(path):
        return {"allocated": {}}
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception:  # noqa: BLE001
        return {"allocated": {}}
    if not isinstance(data, dict) or not isinstance(data.get("allocated"), dict):
        return {"allocated": {}}
    return data


def save_ledger(root, ledger):
    path = os.path.join(root, LEDGER_REL)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(ledger, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")


# ------------------------------------------------------------------ 分配

def die(msg, code=2):
    sys.stderr.write(msg + "\n")
    sys.exit(code)


def validate_name(value, label):
    if not SNAKE.match(value or ""):
        die("%s=%r 不合法：须为 snake_case（^[a-z][a-z0-9_]*$），"
            "连字符只作层级分隔符，不得出现在组件/模块名中" % (label, value))
    return value


def parse_args(argv):
    if len(argv) < 3:
        die(__doc__.strip())
    root = os.path.abspath(argv[1])
    if not os.path.isdir(root):
        die("[FAIL] 项目根目录不存在: %s" % root)
    kind = argv[2]
    opts = {"count": 1, "component": None, "module": "all", "plan_ref": None}
    rest = argv[3:]
    i = 0
    while i < len(rest):
        tok = rest[i]
        if tok == "--count" and i + 1 < len(rest):
            try:
                opts["count"] = int(rest[i + 1])
            except ValueError:
                die("--count 须为整数")
            i += 2
        elif tok.startswith("--count="):
            try:
                opts["count"] = int(tok.split("=", 1)[1])
            except ValueError:
                die("--count 须为整数")
            i += 1
        elif tok == "--component" and i + 1 < len(rest):
            opts["component"] = rest[i + 1]
            i += 2
        elif tok.startswith("--component="):
            opts["component"] = tok.split("=", 1)[1]
            i += 1
        elif tok == "--module" and i + 1 < len(rest):
            opts["module"] = rest[i + 1]
            i += 2
        elif tok.startswith("--module="):
            opts["module"] = tok.split("=", 1)[1]
            i += 1
        elif tok == "--plan-ref" and i + 1 < len(rest):
            opts["plan_ref"] = rest[i + 1]
            i += 2
        elif tok.startswith("--plan-ref="):
            opts["plan_ref"] = tok.split("=", 1)[1]
            i += 1
        else:
            die("未知参数: %r（见文件头用法）" % tok)
    if opts["count"] < 1 or opts["count"] > 500:
        die("--count 须在 1..500 之间")
    return root, kind, opts


def allocate(argv):
    root, kind, opts = parse_args(argv)
    if kind == "check":
        return cmd_check(root)

    max_by_key, _ = scan(root)
    ledger = load_ledger(root)

    if kind == "exec":
        plan_ref = opts["plan_ref"]
        if not plan_ref or not re.match(r"^P-\d{3}$", plan_ref):
            die("--plan-ref 须形如 P-003（数字三位）")
        key = "EXEC:%s" % plan_ref
        start = max(max_by_key.get(key, 0), ledger["allocated"].get(key, 0)) + 1
        ids = ["%s-%d" % (plan_ref, start + i) for i in range(opts["count"])]
        last = start + opts["count"] - 1
    else:
        spec = SPECS.get(kind)
        if spec is None:
            die("未知编号类型: %r（可用：%s、exec、check）"
                % (kind, "、".join(sorted(SPECS))))
        if spec.needs_component:
            if not opts["component"]:
                die("%s 需要 --component <snake_case>" % kind)
            comp = validate_name(opts["component"], "--component")
        if spec.needs_module:
            mod = validate_name(opts["module"], "--module")
        if spec.needs_component and spec.needs_module:
            key = "%s:%s:%s" % (spec.key, comp, mod)
            fmt_args = {"c": comp, "m": mod}
        elif spec.needs_component:
            key = "%s:%s" % (spec.key, comp)
            fmt_args = {"c": comp}
        else:
            key = spec.key
            fmt_args = {}
        start = max(max_by_key.get(key, 0), ledger["allocated"].get(key, 0)) + 1
        ids = []
        for i in range(opts["count"]):
            fmt_args["n"] = start + i
            ids.append(spec.fmt.format(**fmt_args))
        last = start + opts["count"] - 1

    ledger["allocated"][key] = max(last, ledger["allocated"].get(key, 0))
    save_ledger(root, ledger)

    sys.stdout.write(json.dumps({
        "ok": True,
        "type": kind,
        "key": key,
        "ids": ids,
        "ledger": LEDGER_REL.replace(os.sep, "/"),
    }, ensure_ascii=False, indent=2) + "\n")
    return 0


# ------------------------------------------------------------------ 校验

def scan_definitions(root):
    """只收「定义位」上的编号：JSON/JSONL 里 exec_id / plan_id 键、
    RUN 头的 id 键。引用位（EXEC.plan_ref、BUG.source.exec）不计，
    否则合法回指会被误判成重号。"""
    found = []  # (kind, ident, relpath)

    def walk(node, kind_filter):
        if isinstance(node, dict):
            for key, val in node.items():
                if key in ("exec_id", "plan_id") and isinstance(val, str):
                    found.append((key, val, kind_filter))
                else:
                    walk(val, kind_filter)
        elif isinstance(node, list):
            for item in node:
                walk(item, kind_filter)

    for path in walk_text_files(root):
        low = path.lower()
        if not low.endswith((".json", ".jsonl")):
            continue
        rel = os.path.relpath(path, root).replace(os.sep, "/")
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            continue
        if low.endswith(".jsonl"):
            objs = []
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    objs.append(json.loads(line))
                except ValueError:
                    continue
        else:
            try:
                objs = [json.loads(text)]
            except ValueError:
                continue
        for obj in objs:
            walk(obj, rel)
            if isinstance(obj, dict) and isinstance(obj.get("id"), str) \
                    and obj["id"].startswith("RUN-"):
                found.append(("run_id", obj["id"], rel))
    return found


def cmd_check(root):
    _, all_ids = scan(root)
    problems = []

    # 1) 格式：段数、组件/模块 snake_case
    for path, ident in all_ids:
        rel = os.path.relpath(path, root)
        if ident.startswith("fr-") or ident.startswith("biz-"):
            parts = ident.split("-")
            if len(parts) != 4:
                problems.append("%s: %s 段数应为 4（fr/biz-<组件>-<模块>-NNN）；"
                                "组件名疑似含连字符" % (rel, ident))
                continue
            for seg, label in ((parts[1], "组件"), (parts[2], "模块")):
                if not SNAKE.match(seg):
                    problems.append("%s: %s 的%s段 %r 非 snake_case" % (rel, ident, label, seg))
        elif ident.startswith(("CASE-", "TD-", "BUG-", "CR-")) or ident.startswith("NFR-CASE-") \
                or ident.startswith("NFR-TD-"):
            parts = ident.split("-")
            expect = 3 if ident.startswith(("CASE-", "TD-", "BUG-", "CR-")) else 4
            if len(parts) != expect:
                problems.append("%s: %s 段数应为 %d" % (rel, ident, expect))
                continue
            comp = parts[-2]
            if not SNAKE.match(comp):
                problems.append("%s: %s 的组件段 %r 非 snake_case" % (rel, ident, comp))

    # 1b) 段数兜底：严格正则匹配不上的畸形写法（如 fr-order-svc-all-001，
    #     组件名带连字符）会被静默跳过，这里用宽松扫描补一刀。只收全小写 token，
    #     避免误伤文档里的 `fr-<组件>-<模块>-NNN` 占位说明。
    loose = re.compile(r"\b(?:fr|biz)-[a-z0-9][a-z0-9_-]*\b")
    reported = set(problems)
    for path in walk_text_files(root):
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            continue
        rel = os.path.relpath(path, root)
        for m in loose.finditer(text):
            token = m.group(0).rstrip("-")
            segs = token.split("-")
            if len(segs) == 4:
                continue
            msg = ("%s: %s 段数应为 4（实际 %d 段）；组件/模块名含连字符是最常见成因"
                   % (rel, token, len(segs)))
            if msg not in reported:
                reported.add(msg)
                problems.append(msg)

    # 2) 定义位唯一性：P-xxx 全局唯一（跨 RUN）、exec_id 全局唯一、RUN-NNN 唯一
    defs = scan_definitions(root)
    for kind, label in (("plan_id", "实例计划行 P-xxx"),
                        ("exec_id", "执行明细 exec_id"),
                        ("run_id", "执行轮 RUN-NNN")):
        seen = {}
        for key, ident, rel in defs:
            if key != kind:
                continue
            seen.setdefault(ident, []).append(rel)
        for ident, files in sorted(seen.items()):
            if len(files) > 1:
                problems.append("%s %s 被定义 %d 次：%s"
                                % (label, ident, len(files),
                                   "、".join(sorted(set(files))[:4])))

    if problems:
        for p in problems[:40]:
            sys.stdout.write("[FAIL] id-format     %s\n" % p)
        if len(problems) > 40:
            sys.stdout.write("... 另有 %d 条\n" % (len(problems) - 40))
        return 1

    sys.stdout.write("[PASS] id-format     %d 个编号格式与唯一性检查通过\n" % len(all_ids))
    return 0


def main():
    try:
        return allocate(sys.argv)
    except BrokenPipeError:  # pragma: no cover
        return 0


if __name__ == "__main__":
    sys.exit(main())
