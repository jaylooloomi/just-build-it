# SPDX-License-Identifier: MIT
"""Regression tests for removal validation without mutating the real workspace."""
import json
import os
from pathlib import Path
import shlex
import signal
import subprocess
import sys
import time

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / 'plugins/just-build-it/scripts/removability_check.py'
PYTHON = shlex.quote(Path(sys.executable).as_posix())


def git(root, *args):
    return subprocess.run(['git', '-C', str(root), *args], check=True, capture_output=True).stdout


@pytest.fixture
def project(tmp_path):
    git(tmp_path, 'init', '-q', '-b', 'main')
    git(tmp_path, 'config', 'user.name', 'Removal Test')
    git(tmp_path, 'config', 'user.email', 'test@example.invalid')
    (tmp_path / '.git/info/exclude').write_text('.hoard-pipeline/\n', encoding='utf-8')
    (tmp_path / 'source.txt').write_text('committed', encoding='utf-8')
    (tmp_path / 'deleted.txt').write_text('delete me', encoding='utf-8')
    git(tmp_path, 'add', '.')
    git(tmp_path, 'commit', '-qm', 'base')
    # Newly built features are not committed before their gates run.
    (tmp_path / 'features/01-new').mkdir(parents=True)
    (tmp_path / 'features/01-new/feature.txt').write_bytes(b'unchanged feature\n')
    (tmp_path / 'features/flags.json').write_bytes(b'{"01-new": false}\n')
    (tmp_path / '.hoard-pipeline').mkdir()
    return tmp_path


def run(root, command='exit 0', target='features/01-new', **extra):
    (root / '.hoard-pipeline/TEST_CMD').write_text(command, encoding='utf-8')
    return subprocess.run([sys.executable, SCRIPT, target], cwd=root,
                          env=dict(os.environ, CLAUDE_PROJECT_DIR=str(root), **extra),
                          capture_output=True, text=True, timeout=30)


def original_bytes(root):
    return ((root / 'features/01-new/feature.txt').read_bytes(),
            (root / 'features/flags.json').read_bytes(),
            git(root, 'status', '--porcelain', '--untracked-files=all'),
            git(root, 'diff', '--cached', '--binary'))


def assert_cleaned(root):
    # Only the original checkout should remain registered.
    assert git(root, 'worktree', 'list', '--porcelain').count(b'worktree ') == 1


def test_snapshot_sees_uncommitted_source_and_untracked_test(project):
    (project / 'source.txt').write_text('staged version', encoding='utf-8')
    git(project, 'add', 'source.txt')
    (project / 'source.txt').write_text('working version', encoding='utf-8')
    (project / 'deleted.txt').unlink()
    (project / 'untracked.txt').write_text('new file', encoding='utf-8')
    (project / 'check.py').write_text(
        "from pathlib import Path\nimport json\n"
        "assert Path('source.txt').read_text() == 'working version'\n"
        "assert Path('untracked.txt').read_text() == 'new file'\n"
        "assert not Path('deleted.txt').exists()\n"
        "assert not Path('features/01-new').exists()\n"
        "assert json.loads(Path('features/flags.json').read_text()) == {}\n",
        encoding='utf-8')
    before = original_bytes(project)
    result = run(project, PYTHON + ' check.py')
    assert result.returncode == 0, result.stderr + result.stdout
    assert result.stdout.startswith('REMOVABLE:')
    assert original_bytes(project) == before
    assert_cleaned(project)


def test_failed_suite_does_not_edit_real_files(project):
    before = original_bytes(project)
    result = run(project, "printf 'mutated in snapshot' > source.txt; exit 7")
    assert result.returncode == 1, result.stderr
    assert result.stdout.startswith('NOT-REMOVABLE:')
    assert (project / 'source.txt').read_text() == 'committed'
    assert original_bytes(project) == before
    assert_cleaned(project)


def test_inherited_git_index_does_not_override_snapshot(project):
    before = original_bytes(project)
    result = run(project, 'git rev-parse --show-toplevel', GIT_INDEX_FILE=str(project / 'does-not-exist.index'))
    assert result.returncode == 0, result.stderr
    assert not (project / 'does-not-exist.index').exists()
    assert original_bytes(project) == before
    assert_cleaned(project)


@pytest.mark.parametrize('registry', ['{broken', '[]', '{}', '{"01-new": "false"}'])
def test_invalid_flags_fail_closed_without_running_tests(project, registry):
    (project / 'features/flags.json').write_text(registry, encoding='utf-8')
    before = original_bytes(project)
    result = run(project, 'exit 0')
    assert result.returncode == 2
    assert 'REMOVABILITY-ERROR:' in result.stderr
    assert original_bytes(project) == before
    assert_cleaned(project)


def test_missing_flags_fail_closed(project):
    (project / 'features/flags.json').unlink()
    result = run(project)
    assert result.returncode == 2
    assert 'flags.json' in result.stderr
    assert (project / 'features/01-new/feature.txt').read_bytes() == b'unchanged feature\n'
    assert_cleaned(project)


@pytest.mark.parametrize('timeout', ['0', '-1', 'nan', 'infinity', 'invalid'])
def test_invalid_timeout_rejected_before_tests(project, timeout):
    before = original_bytes(project)
    result = run(project, HOARD_TEST_TIMEOUT=timeout)
    assert result.returncode == 2
    assert 'HOARD_TEST_TIMEOUT' in result.stderr
    assert original_bytes(project) == before
    assert_cleaned(project)


def test_missing_test_command_fails_closed(project):
    result = subprocess.run([sys.executable, SCRIPT, 'features/01-new'], cwd=project,
                            env=dict(os.environ, CLAUDE_PROJECT_DIR=str(project)),
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 2
    assert 'TEST_CMD' in result.stderr
    assert_cleaned(project)


@pytest.mark.parametrize('target', ['features/../features/01-new', '../features/01-new', '.', 'source.txt'])
def test_invalid_targets_rejected(project, target):
    before = original_bytes(project)
    result = run(project, target=target)
    assert result.returncode == 2
    assert original_bytes(project) == before
    assert_cleaned(project)


def test_timeout_kills_tests_and_preserves_real_checkout(project):
    before = original_bytes(project)
    result = run(project, 'sleep 30', HOARD_TEST_TIMEOUT='0.1')
    assert result.returncode == 2
    assert 'timed out' in result.stderr
    assert original_bytes(project) == before
    assert_cleaned(project)


def test_ignored_sibling_features_in_snapshot(project):
    (project / '.gitignore').write_text('features/\n', encoding='utf-8')
    (project / 'features/02-ignored').mkdir()
    (project / 'features/02-ignored/sibling.txt').write_text('must remain', encoding='utf-8')
    command = PYTHON + ' -c ' + shlex.quote(
        "from pathlib import Path; assert Path('features/02-ignored/sibling.txt').read_text() == 'must remain'")
    result = run(project, command)
    assert result.returncode == 0, result.stderr + result.stdout
    assert_cleaned(project)


def test_symlink_feature_rejected(project):
    link = project / 'features/02-link'
    try:
        link.symlink_to(project / 'features/01-new', target_is_directory=True)
    except OSError:
        pytest.skip('symlinks unavailable')
    result = run(project, target='features/02-link')
    assert result.returncode == 2
    assert 'symlink' in result.stderr
    assert_cleaned(project)


def test_shared_dependency_directory_is_explicit_and_opt_out_works(project):
    dependency = project / 'node_modules/example'
    dependency.mkdir(parents=True)
    (dependency / 'index.js').write_text('module.exports = 1', encoding='utf-8')
    (project / '.gitignore').write_text('node_modules/\n', encoding='utf-8')
    command = PYTHON + ' -c ' + shlex.quote(
        "from pathlib import Path; assert Path('node_modules/example/index.js').exists()")
    result = run(project, command)
    if result.returncode == 2 and 'cannot link dependency' in result.stderr:
        pytest.skip('directory symlinks unavailable')
    assert result.returncode == 0, result.stderr
    assert (dependency / 'index.js').read_text() == 'module.exports = 1'
    result = run(project, command, HOARD_SHARE_TEST_DEPS='0')
    assert result.returncode == 1
    assert_cleaned(project)


@pytest.mark.skipif(os.name == 'nt', reason='SIGTERM handlers are POSIX; Windows termination covered by timeout test')
def test_interrupt_preserves_original_and_cleans_worktree(project):
    before = original_bytes(project)
    (project / '.hoard-pipeline/TEST_CMD').write_text('sleep 30', encoding='utf-8')
    process = subprocess.Popen([sys.executable, SCRIPT, 'features/01-new'], cwd=project,
                               env=dict(os.environ, CLAUDE_PROJECT_DIR=str(project)),
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        end = time.monotonic() + 10
        log = project / '.hoard-pipeline/removability-01-new.log'
        while not log.exists() and time.monotonic() < end:
            time.sleep(.02)
        assert log.exists()
        assert original_bytes(project) == before
        process.send_signal(signal.SIGTERM)
        output, error = process.communicate(timeout=10)
        assert process.returncode == 2, output + error
        assert 'interrupted' in error
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate()
    assert original_bytes(project) == before
    assert_cleaned(project)
