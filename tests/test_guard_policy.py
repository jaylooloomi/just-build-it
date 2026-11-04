# SPDX-License-Identifier: MIT
"""Regression coverage for shared shell/file frozen-path enforcement."""
import json
import os
import pathlib
import subprocess
import sys

import pytest

SCRIPTS = pathlib.Path(__file__).resolve().parents[1] / 'plugins/just-build-it/scripts'


@pytest.fixture
def guarded(tmp_path):
    pipeline = tmp_path / '.hoard-pipeline'
    pipeline.mkdir()
    (pipeline / 'ACTIVE').touch()
    (pipeline / 'FROZEN').write_text('app/core.py\napp/kernel/\n', encoding='utf-8')
    (tmp_path / 'app/kernel').mkdir(parents=True)
    (tmp_path / 'app/core.py').write_text('original\n')
    (tmp_path / 'app/kernel/run.py').write_text('original\n')
    (tmp_path / 'features/01-new').mkdir(parents=True)
    return tmp_path


def guard(root, script, tool_input):
    return subprocess.run([sys.executable, SCRIPTS / script],
                          input=json.dumps({'tool_input': tool_input}),
                          capture_output=True, text=True, cwd=root,
                          env=dict(os.environ, CLAUDE_PROJECT_DIR=str(root)))


@pytest.mark.parametrize('command', [
    'printf x > app/core.py',
    'printf x >> app/core.py',
    'printf x > app/../app/core.py',
    'sed -i "s/old/new/" app/core.py',
    'sed -i -e "s/old/new/" app/core.py',
    'sed --in-place "s/old/new/" app/core.py',
    'sed -i -es/old/new/ app/core.py',
    'tee app/core.py',
    'truncate -s 0 app/core.py',
    'touch app/core.py',
    'cp other.py app/core.py',
    'cp core.py app',
    'cp -t app core.py',
    'mv app/core.py features/01-new/saved.py',
    'rm app/core.py',
    'rm -r app',
    'mv app elsewhere',
    'dd if=other.py of=app/core.py',
    'bash -c "printf x > app/core.py"',
    'sh -lc "cd app && printf x > core.py"',
    'env -i sed -i s/old/new/ app/core.py',
    'command -- sed -i s/old/new/ app/core.py',
    'bash --norc -c "sed -i s/old/new/ app/core.py"',
    'for n in 1; do rm app/core.py; done',
    '{ rm app/core.py; }',
    'cd app\nprintf x > core.py',
    '( cd features ); printf x > app/core.py',
    'printf x > package-lock.json',
    'printf x > app/../package.json',
    'printf x > "$TARGET"',
    'sed.exe -i s/old/new/ app/core.py',
    '"C:/Program Files/Git/usr/bin/SED.EXE" -i s/old/new/ app/core.py',
    'cp.exe other.py app/core.py',
    'rm.exe app/core.py',
    'bash.exe -c "sed.exe -i s/old/new/ app/core.py"',
    'env.exe -i sed.exe -i s/old/new/ app/core.py',
    'git.exe merge main',
    'git.exe reset --hard',
    'git.exe push origin main',
    'git.exe push --force origin hoard/test',
    'command -v git > app/core.py',
])
def test_known_shell_mutations_block_frozen_or_unresolved(guarded, command):
    result = guard(guarded, 'guard_bash.py', {'command': command})
    assert result.returncode == 2, (command, result.stdout, result.stderr)


@pytest.mark.parametrize('command', [
    'cat app/core.py',
    'git status --short',
    'python -m pytest -q tests',
    'printf x > features/01-new/feature.py',
    'printf ">" app/core.py',
    'printf "app/core.py"',
    'echo message >&2',
    'cat app/core.py > /dev/null',
    'git push -u origin hoard/test',
    'git.exe status --short',
    'git.exe push -u origin hoard/test',
    'command -v git',
    'command -V git',
])
def test_read_only_and_in_scope_shell_commands_allowed(guarded, command):
    result = guard(guarded, 'guard_bash.py', {'command': command})
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize('path', ['app/core.py', 'app/../app/core.py', 'app/kernel/run.py',
                                 'app/../package.json', 'package-lock.json'])
def test_file_tool_uses_identical_policy(guarded, path):
    assert guard(guarded, 'guard_write.py', {'file_path': path}).returncode == 2


def test_patch_move_source_and_destination_checked(guarded):
    patch = '*** Begin Patch\n*** Update File: features/01-new/a.py\n*** Move to: app/core.py\n*** End Patch'
    assert guard(guarded, 'guard_write.py', {'command': patch}).returncode == 2


@pytest.mark.parametrize('script', ['guard_bash.py', 'guard_write.py'])
@pytest.mark.parametrize('contents', [None, '../outside.py\n', '/absolute/path\n', 'app/*.py\n'])
def test_missing_or_invalid_frozen_fails_closed(guarded, script, contents):
    frozen = guarded / '.hoard-pipeline/FROZEN'
    if contents is None:
        frozen.unlink()
    else:
        frozen.write_text(contents)
    tool_input = {'command': 'git status', 'file_path': 'features/01-new/a.py'}
    result = guard(guarded, script, tool_input)
    assert result.returncode == 2 and 'FROZEN' in result.stderr


@pytest.mark.parametrize('script', ['guard_bash.py', 'guard_write.py'])
def test_inactive_guard_ignores_missing_configuration(guarded, script):
    (guarded / '.hoard-pipeline/ACTIVE').unlink()
    (guarded / '.hoard-pipeline/FROZEN').unlink()
    assert guard(guarded, script, {'command': 'rm -rf app', 'file_path': 'app/core.py'}).returncode == 0


def test_symlink_alias_cannot_write_frozen_file(guarded):
    try:
        (guarded / 'alias').symlink_to(guarded / 'app', target_is_directory=True)
    except OSError:
        pytest.skip('Symlink creation unavailable on this host')
    assert guard(guarded, 'guard_write.py', {'file_path': 'alias/core.py'}).returncode == 2
    assert guard(guarded, 'guard_bash.py', {'command': 'printf x > alias/core.py'}).returncode == 2


def test_empty_measured_frozen_list_is_valid(guarded):
    (guarded / '.hoard-pipeline/FROZEN').write_text('# no high-fan-in files\n')
    assert guard(guarded, 'guard_bash.py', {'command': 'git status'}).returncode == 0


def test_moving_parent_cannot_remove_protected_descendants(guarded):
    workflows = guarded / '.github/workflows'
    workflows.mkdir(parents=True)
    (workflows / 'test.yml').write_text('name: test\n')
    assert guard(guarded, 'guard_bash.py', {'command': 'mv .github backup'}).returncode == 2
