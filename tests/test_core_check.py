# SPDX-License-Identifier: MIT
"""Regression cases for core gates that used to report errors as clean."""
import os
from pathlib import Path
import subprocess
import sys

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / 'plugins/just-build-it/scripts/core_check.py'


def git(root, *args):
    return subprocess.run(['git', '-C', str(root), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


@pytest.fixture
def repo(tmp_path):
    git(tmp_path, 'init', '-q', '-b', 'main')
    git(tmp_path, 'config', 'user.email', 'test@example.com')
    git(tmp_path, 'config', 'user.name', 'Test')
    (tmp_path / 'core.py').write_text('original\n', encoding='utf-8')
    git(tmp_path, 'add', '.')
    git(tmp_path, 'commit', '-qm', 'baseline')
    pipeline = tmp_path / '.hoard-pipeline'
    pipeline.mkdir()
    (pipeline / 'BASE').write_text(git(tmp_path, 'rev-parse', 'HEAD'), encoding='utf-8')
    (pipeline / 'FROZEN').write_text('core.py\n', encoding='utf-8')
    return tmp_path


def check(root):
    return subprocess.run([sys.executable, str(SCRIPT)], capture_output=True,
                          text=True, encoding='utf-8',
                          env=dict(os.environ, CLAUDE_PROJECT_DIR=str(root)))


@pytest.mark.parametrize('file,contents', [
    ('BASE', None), ('BASE', ''), ('BASE', 'missing-branch'),
    ('BASE', '--help'), ('BASE', 'main\nHEAD'),
    ('FROZEN', None), ('FROZEN', '../outside.py'),
    ('CORE_BASE', 'missing-mount-commit'),
])
def test_invalid_configuration_never_reports_clean(repo, file, contents):
    path = repo / '.hoard-pipeline' / file
    if contents is None:
        path.unlink()
    else:
        path.write_text(contents, encoding='utf-8')
    result = check(repo)
    assert result.returncode == 2
    assert 'CORE-ERROR:' in result.stderr
    assert 'CORE-CLEAN:' not in result.stdout


def test_non_git_directory_is_an_error(tmp_path):
    result = check(tmp_path)
    assert result.returncode == 2
    assert 'CORE-CLEAN:' not in result.stdout


@pytest.mark.parametrize('change', ['unstaged', 'staged', 'deleted', 'renamed'])
def test_changed_frozen_file_is_rejected(repo, change):
    if change == 'renamed':
        git(repo, 'mv', 'core.py', 'moved.py')
    elif change == 'deleted':
        (repo / 'core.py').unlink()
    else:
        (repo / 'core.py').write_text('changed\n', encoding='utf-8')
        if change == 'staged':
            git(repo, 'add', 'core.py')
    result = check(repo)
    assert result.returncode == 1
    assert 'CORE-TOUCHED: core.py' in result.stdout


def test_frozen_directory_includes_new_files_and_spaces(repo):
    name = 'shared code/new module.py'
    (repo / 'shared code').mkdir()
    (repo / name).write_text('new\n', encoding='utf-8')
    (repo / '.hoard-pipeline/FROZEN').write_text('shared code/\n', encoding='utf-8')
    result = check(repo)
    assert result.returncode == 1
    assert f'CORE-TOUCHED: {name}' in result.stdout


def test_staged_violation_cannot_hide_behind_clean_working_file(repo):
    (repo / 'core.py').write_text('staged violation\n', encoding='utf-8')
    git(repo, 'add', 'core.py')
    (repo / 'core.py').write_text('original\n', encoding='utf-8')
    result = check(repo)
    assert result.returncode == 1
    assert 'CORE-TOUCHED: core.py' in result.stdout


def test_clean_and_non_frozen_changes_pass(repo):
    (repo / 'feature.py').write_text('allowed\n', encoding='utf-8')
    result = check(repo)
    assert result.returncode == 0
    assert 'CORE-CLEAN:' in result.stdout


def test_mount_commit_has_separate_frozen_baseline(repo):
    base = (repo / '.hoard-pipeline/BASE').read_text(encoding='utf-8')
    (repo / 'mount.py').write_text('registry = []\n', encoding='utf-8')
    git(repo, 'add', 'mount.py')
    git(repo, 'commit', '-qm', 'mount point')
    pipeline = repo / '.hoard-pipeline'
    (pipeline / 'CORE_BASE').write_text(git(repo, 'rev-parse', 'HEAD'), encoding='utf-8')
    (pipeline / 'FROZEN').write_text('core.py\nmount.py\n', encoding='utf-8')
    assert check(repo).returncode == 0
    assert (pipeline / 'BASE').read_text(encoding='utf-8') == base
    (repo / 'mount.py').write_text('registry = ["changed"]\n', encoding='utf-8')
    assert check(repo).returncode == 1
