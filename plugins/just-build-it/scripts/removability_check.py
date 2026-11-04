#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run the removal test in a disposable worktree of the current working files.

Original source and flags are never changed. Ignored dependency environments may
be shared through links, so this is filesystem isolation for the removal check,
not a sandbox for arbitrary tests. Set HOARD_SHARE_TEST_DEPS=0 to disable links.
"""
import json
import os
from pathlib import Path, PureWindowsPath
import re
import shutil
import signal
import subprocess
import sys
import tempfile


DEPENDENCIES = {'node_modules', '.venv', 'venv'}
CACHES = {'.git', '.hoard-pipeline', '__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache'}
GIT_CONTEXT = {'GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_COMMON_DIR', 'GIT_PREFIX'}


class CheckError(Exception):
    pass


def git(root, *args):
    environment = {k: v for k, v in os.environ.items() if k not in GIT_CONTEXT}
    result = subprocess.run([shutil.which('git') or 'git', '-C', str(root), *args], capture_output=True,
                            timeout=30, env=environment)
    if result.returncode:
        raise CheckError(result.stderr.decode('utf-8', 'replace').strip() or 'git command failed')
    return result.stdout


def inside(path, root):
    try:
        return os.path.commonpath([str(path.resolve()), str(root.resolve())]) == str(root.resolve())
    except ValueError:
        return False


def require_plain_path(root, relative):
    """Only accept in-repository paths, with no symlink/junction components."""
    path = root
    for part in relative.parts:
        path = path / part
        if path.is_symlink() or (hasattr(path, 'is_junction') and path.is_junction()):
            raise CheckError('feature and flag paths cannot contain symlinks or junctions')
    if not inside(path, root):
        raise CheckError('path escapes the repository')
    return path


def validate(root, argument):
    rel = Path(argument.replace('\\', '/'))
    if (rel.is_absolute() or PureWindowsPath(argument).drive or '..' in rel.parts
            or len(rel.parts) < 2 or rel.parent.name != 'features'
            or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', rel.name)):
        raise CheckError('expected an in-repository features/<slug> directory')
    feature = require_plain_path(root, rel)
    if not feature.is_dir():
        raise CheckError('feature directory does not exist')
    registry = rel.parent / 'flags.json'
    flags_path = require_plain_path(root, registry)
    try:
        flags = json.loads(flags_path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        raise CheckError('flags.json must exist and contain valid JSON: ' + str(exc)) from exc
    if (not isinstance(flags, dict) or not all(isinstance(v, bool) for v in flags.values())
            or rel.name not in flags):
        raise CheckError('flags.json must contain boolean flags, including the feature slug')
    flags.pop(rel.name)
    try:
        command = (root / '.hoard-pipeline/TEST_CMD').read_text(encoding='utf-8').strip()
        timeout = float(os.environ.get('HOARD_TEST_TIMEOUT', '600'))
    except (OSError, ValueError) as exc:
        raise CheckError('TEST_CMD or HOARD_TEST_TIMEOUT is invalid: ' + str(exc)) from exc
    if not command or not 0 < timeout <= 86400:
        raise CheckError('TEST_CMD must be nonempty; HOARD_TEST_TIMEOUT must be in (0, 86400] seconds')
    return rel, registry, flags, command, timeout


def snapshot_paths(root, feature):
    raw = git(root, 'ls-files', '-z', '--cached', '--others', '--exclude-standard')
    files = {Path(os.fsdecode(p)) for p in raw.split(b'\0') if p}
    # Even an ignored feature tree must be represented, including sibling features.
    # Do not traverse installed dependencies or generated interpreter caches.
    feature_roots = {feature.parent}
    for rel in list(files):
        if 'features' in rel.parts:
            feature_roots.add(Path(*rel.parts[:rel.parts.index('features') + 1]))
    for rel in feature_roots:
        base = root / rel
        if base.is_symlink() or not inside(base, root):
            raise CheckError('feature root cannot be an external symlink')
        for directory, dirs, names in os.walk(base, followlinks=False):
            dirs[:] = [d for d in dirs if d not in CACHES | DEPENDENCIES]
            for name in dirs:
                candidate = Path(directory) / name
                if candidate.is_symlink():
                    files.add(candidate.relative_to(root))
            for name in names:
                if not name.endswith(('.pyc', '.pyo')):
                    files.add((Path(directory) / name).relative_to(root))
    return {p for p in files if p.parts and p.parts[0] not in CACHES}


def copy_current(root, worktree, feature):
    files = snapshot_paths(root, feature)
    # A worktree starts at HEAD: remove tracked files deleted in the working copy.
    tracked = git(worktree, 'ls-files', '-z').split(b'\0')
    for raw in tracked:
        if not raw:
            continue
        rel = Path(os.fsdecode(raw))
        original = root / rel
        if not original.exists() and not original.is_symlink():
            target = worktree / rel
            if target.is_symlink() or target.is_file():
                target.unlink()
    for rel in sorted(files):
        original, target = root / rel, worktree / rel
        if not original.exists() and not original.is_symlink():
            continue
        if not inside(target.parent, worktree):
            raise CheckError('snapshot target escapes worktree')
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.is_symlink():
            target.unlink()
        if original.is_symlink():
            resolved = original.resolve()
            if not inside(resolved, root):
                raise CheckError('snapshot cannot include external source symlink: ' + str(rel))
            destination = worktree / resolved.relative_to(root)
            target.symlink_to(os.path.relpath(destination, target.parent), target_is_directory=resolved.is_dir())
        elif original.is_file():
            shutil.copy2(original, target)
        else:
            raise CheckError('submodules and special source files need a dedicated test environment: ' + str(rel))


def link_dependencies(root, worktree):
    if os.environ.get('HOARD_SHARE_TEST_DEPS', '1') == '0':
        return
    # Only recognized ignored dependency directories; never share arbitrary ignored data.
    raw = git(root, 'ls-files', '-z', '--others', '--ignored', '--exclude-standard', '--directory')
    for name in raw.split(b'\0'):
        if not name:
            continue
        rel = Path(os.fsdecode(name).rstrip('/'))
        if rel.name not in DEPENDENCIES:
            continue
        original, target = root / rel, worktree / rel
        if not original.is_dir() or target.exists():
            continue
        if not inside(original, root) or not inside(target.parent, worktree):
            raise CheckError('dependency path escapes repository')
        if 'features' in original.resolve().relative_to(root).parts:
            raise CheckError('shared dependencies cannot refer into feature directories')
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            target.symlink_to(original.resolve(), target_is_directory=True)
        except OSError as exc:
            raise CheckError('cannot link dependency ' + str(rel)
                             + '; prepare a test environment or set HOARD_SHARE_TEST_DEPS=0: ' + str(exc)) from exc


def stop_process(process):
    if os.name == 'nt':
        if process.poll() is not None:
            return
        # Terminate bash and all child test processes, not the caller.
        taskkill = Path(os.environ.get('SystemRoot', 'C:/Windows')) / 'System32/taskkill.exe'
        try:
            subprocess.run([str(taskkill), '/PID', str(process.pid), '/T', '/F'], capture_output=True, timeout=10)
        finally:
            if process.poll() is None:
                process.kill()
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    process.wait()


def run_suite(command, worktree, log, timeout):
    environment = dict(os.environ, CLAUDE_PROJECT_DIR=str(worktree), HOARD_REMOVABILITY_CHECK=str(worktree))
    for key in GIT_CONTEXT:
        environment.pop(key, None)
    options = {'start_new_session': True} if os.name != 'nt' else {
        'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP}
    with log.open('w', encoding='utf-8') as output:
        output.write('Removal verification in disposable worktree; original source remains in place.\n')
        output.flush()
        process = subprocess.Popen([shutil.which('bash') or 'bash', '-c', command], cwd=worktree, env=environment,
                                   stdout=output, stderr=subprocess.STDOUT, **options)
        try:
            return process.wait(timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            raise CheckError('test timed out after ' + str(timeout) + ' seconds; see ' + str(log)) from exc
        finally:
            stop_process(process)


def interrupted(signum, _frame):
    raise CheckError('verification interrupted by signal ' + str(signum))


def main():
    worktree = None
    temporary = None
    root = None
    result = 2
    message = ''
    try:
        if len(sys.argv) != 2:
            raise CheckError('usage: removability_check.sh <relative-feature-dir>')
        root = Path(os.environ.get('CLAUDE_PROJECT_DIR') or git(Path.cwd(), 'rev-parse', '--show-toplevel').decode().strip()).resolve()
        if git(root, 'rev-parse', '--show-toplevel').decode().strip().replace('\\', '/') != root.as_posix():
            raise CheckError('CLAUDE_PROJECT_DIR must be the Git repository root')
        rel, registry, flags, command, timeout = validate(root, sys.argv[1])
        log = root / '.hoard-pipeline' / ('removability-' + rel.name + '.log')
        if os.environ.get('HOARD_REMOVABILITY_CHECK') and Path(os.environ['HOARD_REMOVABILITY_CHECK']).resolve() == root:
            raise CheckError('nested removability checks are not supported')
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, interrupted)
        temporary = Path(tempfile.mkdtemp(prefix='hoard-removal-')).resolve()
        worktree = temporary / 'snapshot'
        git(root, 'worktree', 'add', '--detach', '--quiet', str(worktree), 'HEAD')
        copy_current(root, worktree, rel)
        link_dependencies(root, worktree)
        target = require_plain_path(worktree, rel)
        if not inside(target, worktree) or not target.is_dir():
            raise CheckError('feature missing from current snapshot')
        # The recursive removal target has been resolved and verified inside this disposable worktree.
        shutil.rmtree(target)
        registry_path = require_plain_path(worktree, registry)
        registry_path.write_text(json.dumps(flags, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        code = run_suite(command, worktree, log, timeout)
        result = 0 if code == 0 else 1
        message = ('REMOVABLE: ' if result == 0 else 'NOT-REMOVABLE: ') + rel.as_posix() + ' (isolated removal test; see ' + str(log) + ')'
    except (CheckError, OSError, UnicodeError, ValueError, subprocess.SubprocessError) as exc:
        message = 'REMOVABILITY-ERROR: ' + str(exc)
    finally:
        # Ignore additional interrupt signals while releasing this check's private worktree.
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, signal.SIG_IGN)
        if worktree is not None and worktree.exists():
            try:
                git(root, 'worktree', 'remove', '--force', str(worktree))
            except (CheckError, OSError, subprocess.SubprocessError) as exc:
                result = 2
                message = 'REMOVABILITY-ERROR: worktree cleanup failed: ' + str(exc) + '; retained at ' + str(worktree)
        if temporary is not None and temporary.is_dir() and not (temporary / 'snapshot').exists():
            try:
                temporary.rmdir()
            except OSError as exc:
                result = 2
                message = 'REMOVABILITY-ERROR: temporary directory cleanup failed: ' + str(exc)
    print(message, file=sys.stdout if result < 2 else sys.stderr)
    return result


if __name__ == '__main__':
    sys.exit(main())
