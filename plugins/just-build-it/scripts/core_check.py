#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Verify frozen paths against a valid baseline; errors are never a clean result."""
import os
from pathlib import Path
import subprocess
import sys

from path_policy import PathPolicy, PolicyError, is_frozen, project_root


def git(root, *args):
    result = subprocess.run(
        ['git', '-C', str(root), *args], capture_output=True, timeout=30,
    )
    if result.returncode:
        raise ValueError(result.stderr.decode('utf-8', errors='replace').strip()
                         or 'git command failed')
    return result.stdout


def check(root):
    root = Path(root).resolve()
    top = Path(os.fsdecode(git(root, 'rev-parse', '--show-toplevel')).strip()).resolve()
    if top != root:
        raise ValueError('project root must be the Git worktree root')
    policy = PathPolicy(str(root))
    pipeline = root / '.hoard-pipeline'
    # BASE remains the review/MR base. CORE_BASE freezes the one allowed mount
    # point commit, so that adding its files to FROZEN does not fail forever.
    baseline_file = pipeline / 'CORE_BASE'
    if not baseline_file.exists():
        baseline_file = pipeline / 'BASE'
    baseline = baseline_file.read_text(encoding='utf-8').strip()
    if not baseline or '\n' in baseline or '\r' in baseline:
        raise ValueError(f'{baseline_file.name} must contain one Git revision')
    commit = git(root, 'rev-parse', '--verify', '--end-of-options',
                 baseline + '^{commit}').decode('ascii').strip()
    # No rename collapsing: check both the deleted old name and new name.
    changed = git(root, 'diff', '--name-only', '--no-renames', '-z', commit, '--')
    # A different staged version can still be committed even when the working
    # file was restored to baseline. Verify the index independently as well.
    changed += git(root, 'diff', '--cached', '--name-only', '--no-renames', '-z', commit, '--')
    changed += git(root, 'ls-files', '--others', '--exclude-standard', '-z', '--')
    hits = []
    for name in sorted(set(changed.split(b'\0')) - {b''}):
        rel = os.fsdecode(name)
        # Protected manifests are handled by guards; this gate checks FROZEN.
        if is_frozen(rel.replace('\\', '/'), policy.frozen):
            hits.append(rel)
    for name in hits:
        print(f'CORE-TOUCHED: {name}')
    if hits:
        return 1
    print(f'CORE-CLEAN: frozen paths unchanged relative to {commit}')
    return 0


def main():
    try:
        return check(project_root())
    except (OSError, ValueError, PolicyError, subprocess.SubprocessError) as exc:
        print(f'CORE-ERROR: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
