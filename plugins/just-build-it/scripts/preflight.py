#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Arthur Wang
"""Preflight for just-build-it: project-type check, then coupling check.

Written by a script, not by the model, so the numbers in SCOPE.md are measured.

    python3 preflight.py <repo-root> [--scope <subdir>] [--json]

Outputs (to stdout, and writes files under <root>/.hoard-pipeline/):
  preflight.json   raw numbers
  FROZEN           path prefixes the write-guard will block (core)
  SCOPE.draft.md   draft of SCOPE.md for the agent to finalise

Mode decision (measured, thresholds overridable by env):
  whole   : project is small/loosely coupled and has runnable tests
  module  : coupling is high → iterate inside one module boundary only
  plugin  : excluded product type (ERP / trading engine / no tests + high coupling)
            or an extension point exists → never touch the repo core at all
"""
import json, os, re, sys, collections

IGNORE_DIRS = {'.git', 'node_modules', 'bin', 'obj', 'dist', 'build', '.venv', 'venv', '__pycache__',
               'vendor', 'target', '.hoard-pipeline', '.agent-pipeline', 'coverage', '.next', 'out'}
SRC_EXT = {'.cs', '.ts', '.tsx', '.js', '.jsx', '.vue', '.py', '.go', '.rs', '.java', '.kt', '.rb', '.php'}
TEST_HINT = re.compile(r'(^|/)(tests?|__tests__|spec|specs)(/|$)|\.(test|spec)\.[a-z]+$|Tests?\.cs$|_test\.(go|py)$|test_[^/]+\.py$')

STACKS = [  # (marker file, stack, test cmd, build cmd)
    ('*.sln', 'dotnet', 'dotnet test --no-restore', 'dotnet build --no-restore'),
    ('*.csproj', 'dotnet', 'dotnet test --no-restore', 'dotnet build --no-restore'),
    ('package.json', 'node', 'npm test --silent', 'npm run build --if-present'),
    ('pyproject.toml', 'python', 'python -m pytest -q', ''),
    ('requirements.txt', 'python', 'python -m pytest -q', ''),
    ('go.mod', 'go', 'go test ./...', 'go build ./...'),
    ('Cargo.toml', 'rust', 'cargo test', 'cargo build'),
    ('pom.xml', 'java', 'mvn -q test', 'mvn -q compile'),
    ('build.gradle', 'java', 'gradle test', 'gradle build'),
]

EXCLUDED_TYPES = re.compile(r'\b(erp|ledger|accounting|payroll|trading|exchange|order ?matching|'
                            r'payment ?gateway|billing ?engine|核心交易|撮合|帳務|薪資|金流引擎)\b', re.I)
TYPE_HINTS = [
    ('game', re.compile(r'\b(game|unity|godot|phaser|pixi|canvas|sprite|level|player)\b|遊戲', re.I)),
    ('cli', re.compile(r'\b(cli|command[- ]line|argparse|click|cobra|commander|yargs)\b', re.I)),
    ('web', re.compile(r'\b(react|vue|next|nuxt|angular|svelte|express|fastapi|flask|django|asp\.net|blazor|controller)\b', re.I)),
    ('library', re.compile(r'\b(library|sdk|package|npm publish|nuget|pypi|crate)\b', re.I)),
    ('backend', re.compile(r'\b(api|service|server|grpc|queue|worker|cron)\b', re.I)),
]

IMPORT_RE = {
    '.py': re.compile(r'^\s*(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))', re.M),
    '.ts': re.compile(r'(?:from|import)\s*[\'"]([^\'"]+)[\'"]|require\([\'"]([^\'"]+)[\'"]\)'),
    '.go': re.compile(r'"([^"]+)"'),
    '.cs': re.compile(r'^\s*using\s+([\w.]+)\s*;', re.M),
    '.rs': re.compile(r'^\s*(?:use|mod)\s+([\w:]+)', re.M),
    '.java': re.compile(r'^\s*import\s+([\w.]+)\s*;', re.M),
}
for e in ('.tsx', '.js', '.jsx', '.vue'): IMPORT_RE[e] = IMPORT_RE['.ts']
IMPORT_RE['.kt'] = IMPORT_RE['.java']


def walk(root, scope=None):
    base = os.path.join(root, scope) if scope else root
    for d, dirs, files in os.walk(base):
        dirs[:] = [x for x in dirs if x not in IGNORE_DIRS and not x.startswith('.')]
        for f in files:
            p = os.path.join(d, f)
            yield os.path.relpath(p, root).replace(os.sep, '/')


def detect_stack(root, files):
    import fnmatch
    for marker, stack, test, build in STACKS:
        for f in files:
            if f.count('/') <= 1 and fnmatch.fnmatch(os.path.basename(f), marker):
                return stack, test, build
    return 'unknown', '', ''


def read_text(root, rel, limit=200_000):
    try:
        with open(os.path.join(root, rel), encoding='utf-8', errors='ignore') as fh:
            return fh.read(limit)
    except Exception:
        return ''


def detect_type(root, files):
    corpus = ''
    for cand in ('README.md', 'README.zh-TW.md', 'readme.md', 'package.json', 'pyproject.toml', 'Cargo.toml', 'go.mod'):
        if cand in files: corpus += read_text(root, cand, 20_000) + '\n'
    corpus += '\n'.join(files[:2000])
    excluded = bool(EXCLUDED_TYPES.search(corpus))
    scores = {t: len(rx.findall(corpus)) for t, rx in TYPE_HINTS}
    ptype = max(scores, key=scores.get) if any(scores.values()) else 'unknown'
    ext_point = bool(re.search(r'\b(plugin|extension|addon|hook|middleware)s?\b', corpus, re.I)) or \
        any(re.search(r'(^|/)(plugins?|extensions?|addons?)/', f) for f in files)
    return ptype, excluded, ext_point, scores


def module_of(rel):
    parts = rel.split('/')
    # first meaningful directory under a src-ish root
    skip = {'src', 'lib', 'app', 'Source', 'source', 'pkg', 'internal', 'cmd'}
    parts = [p for p in parts[:-1] if p not in skip]
    return parts[0] if parts else '(root)'


def coupling(root, src_files):
    stems = {}
    for f in src_files:
        stem = os.path.splitext(f)[0]
        stems[stem] = f
        stems[os.path.basename(stem)] = f  # loose match for C#/Java-style namespace imports
    fan_out = collections.Counter(); fan_in = collections.Counter(); edges = set()
    mod_edges = set()
    for f in src_files:
        ext = os.path.splitext(f)[1]
        rx = IMPORT_RE.get(ext)
        if not rx: continue
        txt = read_text(root, f)
        for m in rx.findall(txt):
            tgt = (m if isinstance(m, str) else next((x for x in m if x), '')).strip()
            if not tgt: continue
            cand = None
            if tgt.startswith('.'):
                cand = os.path.normpath(os.path.join(os.path.dirname(f), tgt)).replace(os.sep, '/')
                cand = stems.get(cand) or stems.get(cand + '/index')
            else:
                last = tgt.replace('::', '.').replace('/', '.').split('.')[-1]
                cand = stems.get(last) if ext in ('.cs', '.java', '.kt', '.rs', '.py', '.go') else None
            if cand and cand != f:
                if (f, cand) not in edges:
                    edges.add((f, cand)); fan_out[f] += 1; fan_in[cand] += 1
                    a, b = module_of(f), module_of(cand)
                    if a != b: mod_edges.add((a, b))
    n = max(len(src_files), 1)
    avg_out = sum(fan_out.values()) / n
    hot = [f for f, c in fan_in.items() if c >= 5]
    cycles = sum(1 for a, b in mod_edges if (b, a) in mod_edges) // 2
    top = fan_in.most_common(12)
    modules = collections.Counter(module_of(f) for f in src_files)
    return dict(files=len(src_files), edges=len(edges), avg_fan_out=round(avg_out, 2),
                hot_files=len(hot), hot_ratio=round(len(hot) / n, 3), module_cycles=cycles,
                top_fan_in=top, modules=modules.most_common(15), mod_edges=sorted(mod_edges))


def decide(stack, ptype, excluded, ext_point, has_tests, c):
    hot_t = float(os.environ.get('HOARD_HOT_RATIO', '0.08'))
    cyc_t = int(os.environ.get('HOARD_MAX_CYCLES', '2'))
    reasons = []
    if excluded:
        reasons.append('產品型態在排除清單（ERP／交易／帳務類），核心不可碰')
        return ('plugin' if ext_point else 'module'), reasons
    high = c['hot_ratio'] > hot_t or c['module_cycles'] > cyc_t
    if high:
        reasons.append(f"耦合偏高：hot_ratio={c['hot_ratio']}（門檻 {hot_t}）、module_cycles={c['module_cycles']}（門檻 {cyc_t}）")
    if not has_tests:
        reasons.append('找不到測試：「關掉全綠」無法驗證，第一批輪次必須先補測試')
    if ext_point and high:
        reasons.append('偵測到擴充點（plugin/extension 目錄或機制）→ 走外掛模式最安全')
        return 'plugin', reasons
    if high or not has_tests:
        return 'module', reasons
    reasons.append('低耦合且有測試 → 全專案模式')
    return 'whole', reasons


def main():
    argv = sys.argv[1:]
    root = os.path.abspath(argv[0]) if argv and not argv[0].startswith('--') else os.getcwd()
    scope = None
    if '--scope' in argv: scope = argv[argv.index('--scope') + 1]
    files = list(walk(root, scope))
    all_files = list(walk(root)) if scope else files
    stack, test_cmd, build_cmd = detect_stack(root, all_files)
    ptype, excluded, ext_point, type_scores = detect_type(root, all_files)
    src = [f for f in files if os.path.splitext(f)[1] in SRC_EXT and not TEST_HINT.search(f)]
    tests = [f for f in files if os.path.splitext(f)[1] in SRC_EXT and TEST_HINT.search(f)]
    c = coupling(root, src)
    mode, reasons = decide(stack, ptype, excluded, ext_point, bool(tests), c)
    frozen = [f for f, _ in c['top_fan_in'][:8]]
    if scope: mode = 'module'; reasons.insert(0, f'使用者指定範圍 --scope {scope}')

    out = dict(root=root, scope=scope, stack=stack, test_cmd=test_cmd, build_cmd=build_cmd,
               product_type=ptype, type_scores=type_scores, excluded_type=excluded, extension_point=ext_point,
               src_files=len(src), test_files=len(tests), coupling=c, mode=mode, reasons=reasons, frozen=frozen)
    pd = os.path.join(root, '.hoard-pipeline'); os.makedirs(pd, exist_ok=True)
    with open(os.path.join(pd, 'preflight.json'), 'w', encoding='utf-8') as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)
    with open(os.path.join(pd, 'FROZEN'), 'w', encoding='utf-8') as fh:
        fh.write('# 核心凍結清單：write-guard 會阻擋對這些路徑的修改。由 preflight 量出（扇入最高的檔案），可手動增刪。\n')
        for f in frozen: fh.write(f + '\n')
    with open(os.path.join(pd, 'SCOPE.draft.md'), 'w', encoding='utf-8') as fh:
        fh.write(scope_md(out))
    if '--json' in argv:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print(scope_md(out))


def scope_md(o):
    c = o['coupling']
    lines = [f"# SCOPE（由 preflight.py 量出，{o['stack']} / {o['product_type']}）", '',
             '## 1. 專案類型', f"- 技術棧：{o['stack']}；測試指令：`{o['test_cmd'] or '未知，agent 必須先找出'}`；建置：`{o['build_cmd'] or '—'}`",
             f"- 產品型態：{o['product_type']}（排除型態：{'是' if o['excluded_type'] else '否'}；擴充點：{'有' if o['extension_point'] else '無'}）",
             f"- 原始碼檔數：{o['src_files']}；測試檔數：{o['test_files']}", '',
             '## 2. 耦合度',
             f"- 檔案依賴邊：{c['edges']}；平均扇出：{c['avg_fan_out']}；熱點檔（扇入≥5）：{c['hot_files']}（比例 {c['hot_ratio']}）；模組循環依賴：{c['module_cycles']}",
             '- 扇入最高的檔案（＝核心凍結候選）：']
    for f, n in c['top_fan_in'][:8]: lines.append(f'  - `{f}`（被 {n} 個檔案引用）')
    lines += ['', f"## 3. 模式判定：**{o['mode']}**"]
    for r in o['reasons']: lines.append(f'- {r}')
    lines += ['', '## 4. 邊界', f"- 迭代範圍：{o['scope'] or ('整個 repo' if o['mode']=='whole' else '（module 模式：agent 在下方填入選定的模組與其對外介面）')}",
              '- 不准碰：見 `.hoard-pipeline/FROZEN`（write-guard 強制）＋ 禁改清單（CI／migration／設定檔／依賴清單）',
              '- 功能落點：`<範圍>/features/<NN-slug>/`，flag 註冊於 `<範圍>/features/flags.json`', '',
              '## 5. 模組一覽（module 模式挑選用）']
    for m, n in c['modules']: lines.append(f'- {m}：{n} 個檔案')
    return '\n'.join(lines) + '\n'


if __name__ == '__main__':
    main()
