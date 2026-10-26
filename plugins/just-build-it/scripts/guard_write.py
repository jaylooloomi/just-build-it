#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Arthur Wang
"""PreToolUse(Write|Edit|MultiEdit|apply_patch) guard for hoarding sessions.

Claude Code sends tool_input.file_path. Codex sends apply_patch with the whole
patch in tool_input.command; target paths are read from its
'*** Add/Update/Delete File:' and '*** Move to:' headers.
Exit 2 + stderr = block. Exit 0 = allow.
"""
import json, os, re, subprocess, sys

PROTECTED = re.compile(
    r'(\.gitlab-ci\.yml$|\.github/workflows/|(^|/)[Mm]igrations?/|appsettings[^/]*\.json$|(^|/)\.env'
    r'|web\.config$|app\.config$|\.csproj$|(^|/)package\.json$|package-lock\.json$|pnpm-lock\.yaml$'
    r'|yarn\.lock$|requirements[^/]*\.txt$|Directory\.Packages\.props$)')
PATCH_HDR = re.compile(r'^\*\*\* (?:Add|Update|Delete) File: (.+)$|^\*\*\* Move to: (.+)$', re.M)

def log_block(root, rule, detail):
    """Append every blocked attempt to .hoard-pipeline/blocked.log — written by the hook, not the model."""
    try:
        import datetime
        line = detail.replace('\n', ' ⏎ ')[:300]
        with open(os.path.join(root, '.hoard-pipeline', 'blocked.log'), 'a', encoding='utf-8') as f:
            f.write(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\t{rule}\t{line}\n")
    except Exception:
        pass

def load_frozen(root):
    """Lines of .hoard-pipeline/FROZEN: path prefixes (dirs end with /) or exact files. Written by preflight.py, editable by the user."""
    try:
        with open(os.path.join(root, '.hoard-pipeline', 'FROZEN'), encoding='utf-8') as f:
            return [l.strip() for l in f if l.strip() and not l.startswith('#')]
    except Exception:
        return []

def is_frozen(rel, frozen):
    rel = rel.replace(os.sep, '/')
    for pat in frozen:
        pat = pat.replace(os.sep, '/')
        if pat.endswith('/') and (rel == pat.rstrip('/') or rel.startswith(pat)):
            return True
        if rel == pat:
            return True
    return False

def project_root():
    r = os.environ.get('CLAUDE_PROJECT_DIR')
    if r: return r
    try:
        return subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True, timeout=5).stdout.strip() or os.getcwd()
    except Exception:
        return os.getcwd()

def main():
    root = project_root()
    if not os.path.isfile(os.path.join(root, '.hoard-pipeline', 'ACTIVE')):
        return
    try:
        ti = json.load(sys.stdin).get('tool_input', {}) or {}
    except Exception:
        return
    paths = []
    for k in ('file_path', 'path'):
        if isinstance(ti.get(k), str): paths.append(ti[k])
    cmd = ti.get('command') if isinstance(ti.get('command'), str) else ''
    if '*** Begin Patch' in cmd or '*** Update File:' in cmd or '*** Add File:' in cmd:
        paths += [(a or b).strip() for a, b in PATCH_HDR.findall(cmd)]
    frozen = load_frozen(root)
    for p in paths:
        rel = os.path.relpath(os.path.abspath(os.path.join(root, p)), root) if not os.path.isabs(p) else os.path.relpath(p, root)
        if frozen and is_frozen(rel, frozen):
            log_block(root, '核心凍結', rel)
            sys.stderr.write(f"囤貨防線阻擋：{rel} 在核心凍結清單（.hoard-pipeline/FROZEN）。功能只能掛在核心上，不能改核心；改寫成獨立模組＋feature flag，或記錄到 CATALOG.md「需要你決定的事」。\n")
            sys.exit(2)
        if PROTECTED.search(p):
            log_block(root, '禁改清單', p)
            sys.stderr.write(f"囤貨防線阻擋：{p} 在禁改清單（CI 設定 / migration / 設定檔 / 依賴清單）。請記錄到 CATALOG.md「需要你決定的事」。\n")
            sys.exit(2)

if __name__ == '__main__':
    main()
