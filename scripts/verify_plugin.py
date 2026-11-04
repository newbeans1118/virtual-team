#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""virtual-team-plugin 结构校验（仅用标准库）。

用法：
    python scripts/verify_plugin.py

退出码：0 = 全部通过；1 = 存在失败项。
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGIN_DIR = os.path.join(ROOT, '.codebuddy-plugin')

SKIP_DIRS = {'.git', '.workbuddy', 'build', '__pycache__', 'node_modules'}
TEXT_EXTS = ('.md', '.json', '.sql', '.jsonl')

failures = []   # (rule, location, detail)
passes = []     # (rule, detail)


def rel(path):
    return os.path.relpath(path, ROOT).replace(os.sep, '/')


def fail(rule, location, detail):
    failures.append((rule, location, detail))


def ok(rule, detail):
    passes.append((rule, detail))


def iter_files(exts=TEXT_EXTS):
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if fn.endswith(exts):
                yield os.path.join(dirpath, fn)


def read(path):
    return open(path, encoding='utf-8').read()


# ---------------------------------------------------------------- 1. JSON
def check_json():
    targets = sorted(glob.glob(os.path.join(ROOT, 'templates', '*.json')))
    targets += sorted(glob.glob(os.path.join(ROOT, 'schemas', '*.json')))
    targets += [
        os.path.join(PLUGIN_DIR, 'plugin.json'),
        os.path.join(PLUGIN_DIR, 'marketplace.json'),
    ]
    for path in targets:
        if not os.path.exists(path):
            fail('json', rel(path), '文件不存在')
            continue
        try:
            json.load(open(path, encoding='utf-8'))
        except Exception as exc:  # noqa: BLE001
            fail('json', rel(path), str(exc))
    ok('json', '%d 个 JSON 合法' % len(targets))


# ---------------------------------------------------- 2. frontmatter name
def frontmatter(text):
    lines = text.splitlines()
    if not lines or lines[0].strip() != '---':
        return None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == '---':
            return '\n'.join(lines[1:idx])
    return None


def check_frontmatter():
    count = 0
    for path in sorted(glob.glob(os.path.join(ROOT, 'skills', '*', 'SKILL.md'))):
        expected = os.path.basename(os.path.dirname(path))
        block = frontmatter(read(path))
        if block is None:
            fail('frontmatter', rel(path), '缺少 frontmatter')
            continue
        match = re.search(r'^name:\s*(\S+)', block, re.M)
        if not match:
            fail('frontmatter', rel(path), '缺少 name 字段')
        elif match.group(1) != expected:
            fail('frontmatter', rel(path), 'name=%s ≠ 目录=%s' % (match.group(1), expected))
        count += 1
    for path in sorted(glob.glob(os.path.join(ROOT, 'agents', '*.md'))):
        expected = os.path.splitext(os.path.basename(path))[0]
        block = frontmatter(read(path))
        if block is None:
            fail('frontmatter', rel(path), '缺少 frontmatter')
            continue
        match = re.search(r'^name:\s*(\S+)', block, re.M)
        if not match:
            fail('frontmatter', rel(path), '缺少 name 字段')
        elif match.group(1) != expected:
            fail('frontmatter', rel(path), 'name=%s ≠ 文件名=%s' % (match.group(1), expected))
        count += 1
    ok('frontmatter', '%d 个技能/角色 name 与目录一致' % count)


# -------------------------------------------------------- 3. plugin.json 路径
def check_plugin_paths():
    path = os.path.join(PLUGIN_DIR, 'plugin.json')
    data = json.load(open(path, encoding='utf-8'))
    total = 0
    for key in ('skills', 'agents', 'rules'):
        for item in data.get(key, []):
            total += 1
            target = os.path.normpath(os.path.join(ROOT, item))
            if not os.path.exists(target):
                fail('plugin-path', item, 'plugin.json %s 路径不存在' % key)
    commands = data.get('commands')
    if commands:
        total += 1
        if not os.path.isdir(os.path.normpath(os.path.join(ROOT, commands))):
            fail('plugin-path', commands, 'commands 目录不存在')
    ok('plugin-path', '%d 条路径全部存在' % total)


# ------------------------------------------------------------ 4. 术语黑名单
BANNED = [
    ('legacy-name', re.compile(r'req-structure|REQ-STRUCTURE|requirement-review')),
    ('legacy-path', re.compile(r'req_functions|req_source_hash|RV-REQ|requirements/')),
    ('legacy-term', re.compile(r'需求评审|需求追踪矩阵|需求说明书|规格说明书|软件PRD|需求PRD')),
    ('legacy-spec', re.compile(r'\bspec(?![-\w])|\bSPEC(?![-\w])|spec-ui|spec-svc|spec-nonfunc|SPEC-MOD|SPEC-NONFUNC')),
    ('legacy-req', re.compile(r'\breq(?![-\w])|idx_req_')),
]

# 有意保留：原文陈述、迁移历史注记、本文档对黑名单自身的说明
WHITELIST_LINE_MARKERS = ('产物称', '契约版本', '术语黑名单', 'spec compliance')


def check_terms():
    hits = 0
    for path in iter_files():
        if os.path.basename(path) == 'statement.txt':
            continue
        text = read(path)
        for lineno, line in enumerate(text.splitlines(), 1):
            if any(marker in line for marker in WHITELIST_LINE_MARKERS):
                continue
            for rule, rx in BANNED:
                if rx.search(line):
                    fail(rule, '%s:%d' % (rel(path), lineno), line.strip()[:100])
                    hits += 1
    if hits == 0:
        ok('terms', '无 legacy spec/req 用语（白名单除外）')


# --------------------------------------------------------------- 5. 版本一致
def check_version():
    plugin = json.load(open(os.path.join(PLUGIN_DIR, 'plugin.json'), encoding='utf-8'))
    market = json.load(open(os.path.join(PLUGIN_DIR, 'marketplace.json'), encoding='utf-8'))
    versions = {
        'plugin.json': plugin.get('version'),
        'marketplace.metadata': (market.get('metadata') or {}).get('version'),
        'marketplace.plugins[0]': ((market.get('plugins') or [{}])[0]).get('version'),
    }
    if len(set(versions.values())) != 1:
        fail('version', 'plugin/marketplace', str(versions))
    else:
        ok('version', '三处版本一致：%s' % versions['plugin.json'])


# ------------------------------------------------------ 6. README 计数一致
def check_readme_counts():
    path = os.path.join(ROOT, 'README.md')
    text = read(path)
    actual = {
        'agents': len(glob.glob(os.path.join(ROOT, 'agents', '*.md'))),
        'skills': len(glob.glob(os.path.join(ROOT, 'skills', '*', 'SKILL.md'))),
        'commands': len(glob.glob(os.path.join(ROOT, 'commands', '*.md'))),
        'templates': len(glob.glob(os.path.join(ROOT, 'templates', '*'))),
    }
    head = re.search(
        r'(\d+) 个角色 agent \+ (\d+) 个技能 skill \+ (\d+) 个工作流命令 \+ (\d+) 个交付物模版',
        text,
    )
    if not head:
        fail('readme-count', 'README.md', '未找到能力计数行')
    else:
        declared = {
            'agents': int(head.group(1)),
            'skills': int(head.group(2)),
            'commands': int(head.group(3)),
            'templates': int(head.group(4)),
        }
        for key, value in declared.items():
            if value != actual[key]:
                fail('readme-count', 'README.md', '声明 %s=%d，实际 %d' % (key, value, actual[key]))
    tree_patterns = {
        'agents': r'# (\d+) 个角色',
        'skills': r'# (\d+) 个技能',
        'commands': r'# (\d+) 个工作流入口',
        'templates': r'# (\d+) 个交付物模版',
    }
    for key, pattern in tree_patterns.items():
        match = re.search(pattern, text)
        if match and int(match.group(1)) != actual[key]:
            fail('readme-count', 'README.md', '目录树声明 %s=%s，实际 %d' % (key, match.group(1), actual[key]))
    if not [f for f in failures if f[0] == 'readme-count']:
        ok('readme-count', '4 项计数与目录一致（agents/skills/commands/templates）')


# -------------------------------------------------------- 7. 模板/技能引用存在
# 插件自带的脚本：引用必须能在插件根下找到
PLUGIN_SCRIPTS = {'verify_plugin.py', 'verify_artifacts.py', 'id_alloc.py'}
# 目标项目侧脚本：由同名模板生成，不在插件根下
PROJECT_SCRIPTS = {'verify.sh'}


def check_references():
    checked = 0
    # 注意：jsonl 必须排在 json 之前，否则 templates/EXEC.jsonl 会被截成不存在的 EXEC.json
    tpl_re = re.compile(r'templates/([A-Za-z0-9._-]+\.(?:jsonl|json|md|sql|sh))')
    for path in iter_files(('.md', '.txt')):
        text = read(path)
        for match in tpl_re.finditer(text):
            checked += 1
            target = os.path.join(ROOT, 'templates', match.group(1))
            if not os.path.exists(target):
                fail('ref-template', '%s' % rel(path), 'templates/%s 不存在' % match.group(1))
        for match in re.finditer(r'skills/([a-z][a-z0-9-]+)', text):
            checked += 1
            target = os.path.join(ROOT, 'skills', match.group(1))
            if not os.path.isdir(target):
                fail('ref-skill', '%s' % rel(path), 'skills/%s 不存在' % match.group(1))
        for match in re.finditer(r'scripts/([A-Za-z0-9._-]+\.(?:py|sh))', text):
            name = match.group(1)
            if name in PLUGIN_SCRIPTS:
                checked += 1
                target = os.path.join(ROOT, 'scripts', name)
                if not os.path.exists(target):
                    fail('ref-script', '%s' % rel(path), 'scripts/%s 不存在' % name)
            elif name in PROJECT_SCRIPTS:
                # 目标项目侧脚本（由模板生成），不在插件根下；改验模板是否存在
                checked += 1
                if not os.path.exists(os.path.join(ROOT, 'templates', name)):
                    fail('ref-script', '%s' % rel(path),
                         'scripts/%s 属目标项目产物，但 templates/%s 模板缺失' % (name, name))
    ok('refs', '%d 条模板/技能/脚本引用已校验' % checked)


# --------------------------------------------------------- 8. README 命令存在
def check_commands():
    text = read(os.path.join(ROOT, 'README.md'))
    names = set(re.findall(r'^\|\s*`/([a-z][a-z0-9-]*)`\s*\|', text, re.M))
    checked = 0
    for name in sorted(names):
        checked += 1
        if not os.path.exists(os.path.join(ROOT, 'commands', name + '.md')):
            fail('ref-command', 'README.md', '/%s 无对应命令文件' % name)
    ok('refs', '%d 个命令入口已校验' % checked)


# ------------------------------------- 9. 模板即合法实例（模板 ↔ schema 一致性）
TEMPLATE_SCHEMA_PAIRS = (
    ('STORE-CONFIG.json', 'store-config'),
    ('PRD-STRUCTURE.json', 'prd-structure'),
    ('CASE-STRUCTURE.json', 'case-structure'),
    ('TD-REGISTRY.json', 'td-registry'),
    ('RUN.json', 'run'),
    ('EXEC-PLAN.json', 'exec-plan'),
    ('BUG.json', 'bug'),
)


def check_template_schema():
    """模板必须是能通过对应 schema 的合法实例样例；AI 照抄不得产出非法产物。"""
    import json as _json
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from verify_artifacts import schema_validate
    except Exception as exc:  # noqa: BLE001
        fail('template-schema', 'scripts/verify_artifacts.py', '无法导入 schema_validate: %s' % exc)
        return
    checked = 0
    total = len(TEMPLATE_SCHEMA_PAIRS) + 1  # + EXEC.jsonl
    for tpl, name in TEMPLATE_SCHEMA_PAIRS:
        try:
            with open(os.path.join(ROOT, 'templates', tpl), encoding='utf-8') as fh:
                data = _json.load(fh)
            with open(os.path.join(ROOT, 'schemas', name + '.schema.json'), encoding='utf-8') as fh:
                schema = _json.load(fh)
        except Exception as exc:  # noqa: BLE001
            fail('template-schema', tpl, '读取/解析失败: %s' % exc)
            continue
        errs = schema_validate(data, schema, tpl)
        if errs:
            for e in errs[:5]:
                fail('template-schema', tpl, e)
        else:
            checked += 1
    try:
        with open(os.path.join(ROOT, 'templates', 'EXEC.jsonl'), encoding='utf-8') as fh:
            lines = [ln.strip() for ln in fh if ln.strip()]
        with open(os.path.join(ROOT, 'schemas', 'exec-line.schema.json'), encoding='utf-8') as fh:
            line_schema = _json.load(fh)
        ok_line = True
        for idx, line in enumerate(lines, 1):
            try:
                errs = schema_validate(_json.loads(line), line_schema, 'EXEC.jsonl:%d' % idx)
            except Exception as exc:  # noqa: BLE001
                fail('template-schema', 'EXEC.jsonl:%d' % idx, 'JSONL 行解析失败: %s' % exc)
                ok_line = False
                continue
            if errs:
                ok_line = False
                for e in errs[:5]:
                    fail('template-schema', 'EXEC.jsonl:%d' % idx, e)
        if ok_line:
            checked += 1
    except Exception as exc:  # noqa: BLE001
        fail('template-schema', 'EXEC.jsonl', '读取失败: %s' % exc)
    if checked == total:
        ok('template-schema', '%d 个模板全部通过对应 schema（合法实例样例）' % checked)


def main():
    check_json()
    check_frontmatter()
    check_plugin_paths()
    check_terms()
    check_version()
    check_readme_counts()
    check_references()
    check_commands()
    check_template_schema()

    for rule, detail in passes:
        print('[PASS] %-14s %s' % (rule, detail))
    if failures:
        print('')
        for rule, location, detail in failures:
            print('[FAIL] %-14s %s | %s' % (rule, location, detail))
        print('\n结果：%d 项通过，%d 处失败' % (len(passes), len(failures)))
        return 1
    print('\n结果：全部通过（%d 项检查）' % len(passes))
    return 0


if __name__ == '__main__':
    sys.exit(main())
