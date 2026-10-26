# SPDX-License-Identifier: MIT
import json, os, subprocess, sys, textwrap, time, pathlib, shutil
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
S = ROOT / 'plugins/just-build-it/scripts'
sys.path.insert(0, str(S))
import preflight as pf  # noqa


def git_repo(tmp_path):
    subprocess.run(['git', 'init', '-q', '-b', 'main', str(tmp_path)], check=True)
    subprocess.run(['git', '-C', str(tmp_path), 'config', 'user.email', 't@t'], check=True)
    subprocess.run(['git', '-C', str(tmp_path), 'config', 'user.name', 't'], check=True)
    return tmp_path


def make_py_project(root, hot=False):
    (root / 'README.md').write_text('# todo cli\nA command-line todo app with argparse.\n')
    (root / 'requirements.txt').write_text('')
    (root / 'app').mkdir()
    (root / 'app/core.py').write_text('def run(): return 1\n')
    for i in range(10):
        imp = 'from app.core import run\n' if hot else ''
        (root / f'app/m{i}.py').write_text(imp + f'def f{i}(): return {i}\n')
    (root / 'tests').mkdir()
    (root / 'tests/test_core.py').write_text('from app.core import run\ndef test_run(): assert run()==1\n')


def test_preflight_whole_mode(tmp_path):
    make_py_project(tmp_path)
    out = json.loads(subprocess.run([sys.executable, S / 'preflight.py', str(tmp_path), '--json'], capture_output=True, text=True, check=True).stdout)
    assert out['stack'] == 'python' and out['product_type'] == 'cli'
    assert out['mode'] == 'whole'
    assert (tmp_path / '.hoard-pipeline/FROZEN').exists()
    assert (tmp_path / '.hoard-pipeline/SCOPE.draft.md').read_text().startswith('# SCOPE')


def test_preflight_module_mode_when_hot(tmp_path, monkeypatch):
    make_py_project(tmp_path, hot=True)
    monkeypatch.setenv('HOARD_HOT_RATIO', '0.05')
    out = json.loads(subprocess.run([sys.executable, S / 'preflight.py', str(tmp_path), '--json'], capture_output=True, text=True, check=True).stdout)
    assert out['coupling']['hot_files'] == 1
    assert out['mode'] == 'module'
    assert 'app/core.py' in out['frozen']


def test_preflight_excluded_type(tmp_path):
    make_py_project(tmp_path)
    (tmp_path / 'README.md').write_text('# ERP\n企業資源規劃 ERP ledger accounting\n')
    out = json.loads(subprocess.run([sys.executable, S / 'preflight.py', str(tmp_path), '--json'], capture_output=True, text=True, check=True).stdout)
    assert out['excluded_type'] and out['mode'] in ('module', 'plugin')


def test_scope_override_forces_module(tmp_path):
    make_py_project(tmp_path)
    out = json.loads(subprocess.run([sys.executable, S / 'preflight.py', str(tmp_path), '--scope', 'app', '--json'], capture_output=True, text=True, check=True).stdout)
    assert out['mode'] == 'module' and out['scope'] == 'app'


def run_guard(root, tool_input, script='guard_write.py'):
    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(root))
    return subprocess.run([sys.executable, S / script], input=json.dumps({'tool_input': tool_input}), capture_output=True, text=True, env=env)


def test_write_guard_blocks_frozen_only_when_active(tmp_path):
    p = tmp_path / '.hoard-pipeline'; p.mkdir()
    (p / 'FROZEN').write_text('# core\napp/core.py\nsrc/kernel/\n')
    r = run_guard(tmp_path, {'file_path': 'app/core.py'})
    assert r.returncode == 0  # not ACTIVE → no interference
    (p / 'ACTIVE').touch()
    assert run_guard(tmp_path, {'file_path': 'app/core.py'}).returncode == 2
    assert run_guard(tmp_path, {'file_path': str(tmp_path / 'src/kernel/x.py')}).returncode == 2
    assert run_guard(tmp_path, {'file_path': 'app/features/01-x/x.py'}).returncode == 0
    assert run_guard(tmp_path, {'file_path': 'package.json'}).returncode == 2  # protected list still applies
    assert 'blocked.log' in os.listdir(p)


def test_bash_guard_branch_prefix(tmp_path):
    p = tmp_path / '.hoard-pipeline'; p.mkdir(); (p / 'ACTIVE').touch()
    assert run_guard(tmp_path, {'command': 'git push -u origin hoard/2026-10-26'}, 'guard_bash.py').returncode == 0
    assert run_guard(tmp_path, {'command': 'git push -u origin night-shift/x'}, 'guard_bash.py').returncode == 2
    assert run_guard(tmp_path, {'command': 'git merge main'}, 'guard_bash.py').returncode == 2


def run_stop(root, env_extra=None):
    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(root), **(env_extra or {}))
    return subprocess.run(['bash', S / 'hoard-stop.sh'], capture_output=True, text=True, env=env)


def test_stop_hook_phases(tmp_path):
    p = tmp_path / '.hoard-pipeline'; p.mkdir()
    assert run_stop(tmp_path).returncode == 0            # inactive
    (p / 'ACTIVE').touch(); (p / 'BASE').write_text('main')
    now = int(time.time())
    (p / 'START').write_text(str(now - 3600)); (p / 'DEADLINE').write_text(str(now + 3600))
    r = run_stop(tmp_path); assert r.returncode == 2 and '囤貨進行中' in r.stderr
    assert (p / 'STATE').read_text().strip() == 'hoarding'
    # last 10% (of 2h = 12min, floor 15min) → packaging
    (p / 'DEADLINE').write_text(str(now + 600))
    r = run_stop(tmp_path); assert r.returncode == 2 and '打包階段' in r.stderr
    assert (p / 'STATE').read_text().strip() == 'packaging'
    # deadline passed → finishing, then allowed to stop
    (p / 'DEADLINE').write_text(str(now - 1))
    r = run_stop(tmp_path); assert r.returncode == 2 and '收工' in r.stderr
    assert run_stop(tmp_path).returncode == 0


def test_stop_hook_user_stop(tmp_path):
    p = tmp_path / '.hoard-pipeline'; p.mkdir(); (p / 'ACTIVE').touch()
    now = int(time.time()); (p / 'START').write_text(str(now)); (p / 'DEADLINE').write_text(str(now + 36000))
    (p / 'STOP').touch()
    r = run_stop(tmp_path); assert r.returncode == 2 and '使用者喊停' in r.stderr


def test_coupling_audit_flags_cross_feature(tmp_path):
    (tmp_path / 'features/01-a').mkdir(parents=True); (tmp_path / 'features/02-b').mkdir(parents=True)
    (tmp_path / 'features/01-a/a.py').write_text('x=1\n')
    (tmp_path / 'features/02-b/b.py').write_text('from features.01_a import a\n')
    out = json.loads(subprocess.run([sys.executable, S / 'coupling_audit.py', str(tmp_path)], capture_output=True, text=True, check=True).stdout)
    assert out['features'] == 2
    warn = (tmp_path / '.hoard-pipeline/coupling-warn.md').read_text()
    assert ('02-b' in warn) == (out['cross_edges'] > 0)


def test_removability_and_core_check(tmp_path):
    root = git_repo(tmp_path); make_py_project(root)
    (root / 'app/__init__.py').write_text('')
    (root / 'app/features/01-hello').mkdir(parents=True)
    (root / 'app/features/flags.json').write_text('{"01-hello": false}')
    (root / 'app/features/01-hello/hello.py').write_text('def hi(): return "hi"\n')
    (root / 'app/features/01-hello/test_hello.py').write_text('from .hello import hi\ndef test_hi(): assert hi()=="hi"\n')
    subprocess.run(['git', '-C', str(root), 'add', '-A'], check=True)
    subprocess.run(['git', '-C', str(root), 'commit', '-qm', 'base'], check=True)
    p = root / '.hoard-pipeline'; p.mkdir()
    (p / 'BASE').write_text('main'); (p / 'FROZEN').write_text('app/core.py\n')
    (p / 'TEST_CMD').write_text(f'{sys.executable} -m pytest -q tests')
    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(root))
    r = subprocess.run(['bash', S / 'removability_check.sh', 'app/features/01-hello'], capture_output=True, text=True, env=env)
    assert r.returncode == 0 and 'REMOVABLE' in r.stdout
    assert (root / 'app/features/01-hello/hello.py').exists()        # restored
    assert json.loads((root / 'app/features/flags.json').read_text()) == {'01-hello': False}  # restored
    # core untouched → clean
    r = subprocess.run(['bash', S / 'core_check.sh'], capture_output=True, text=True, env=env, cwd=root)
    assert r.returncode == 0 and 'CORE-CLEAN' in r.stdout
    (root / 'app/core.py').write_text('def run(): return 2\n')
    r = subprocess.run(['bash', S / 'core_check.sh'], capture_output=True, text=True, env=env, cwd=root)
    assert r.returncode == 1 and 'CORE-TOUCHED' in r.stdout


def test_preflight_scans_debt_and_docs(tmp_path):
    make_py_project(tmp_path)
    (tmp_path / 'app/m1.py').write_text('# TODO: handle empty input\ndef f1(): return 1\n')
    (tmp_path / 'tests/test_core.py').write_text('import pytest\n@pytest.mark.skip\ndef test_x(): pass\n')
    (tmp_path / 'docs').mkdir(); (tmp_path / 'docs/adr-001.md').write_text('# ADR\n')
    out = json.loads(subprocess.run([sys.executable, S / 'preflight.py', str(tmp_path), '--json'], capture_output=True, text=True, check=True).stdout)
    assert out['debt']['todo_count'] == 1 and out['debt']['skip_count'] == 1
    assert out['debt']['todos'][0][0] == 'app/m1.py'
    assert 'README.md' in out['docs'] and 'docs/adr-001.md' in out['docs']
    draft = (tmp_path / '.hoard-pipeline/SCOPE.draft.md').read_text()
    assert '## 0. 專案目的' in draft and '## 2b. 既有債務' in draft and 'app/m1.py:1' in draft
