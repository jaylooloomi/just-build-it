#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Arthur Wang
"""PreToolUse(Bash) guard for hoarding sessions.

Checks known write operations with the shared canonical path policy. Shell
wrappers are inspected recursively. This is not a sandbox: arbitrary programs
and interpreter bodies still require the post-operation core check.
Exit 2 + stderr = block. Exit 0 = allow.
"""
import json, os, re, shlex, subprocess, sys
from path_policy import PathPolicy, PolicyError, project_root

ROOT = None
CMD = ''
POLICY = None

def log_block(root, rule, detail):
    """Append every blocked attempt to .hoard-pipeline/blocked.log — written by the hook, not the model."""
    try:
        import datetime
        line = detail.replace('\n', ' ⏎ ')[:300]
        with open(os.path.join(root, '.hoard-pipeline', 'blocked.log'), 'a', encoding='utf-8') as f:
            f.write(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\t{rule}\t{line}\n")
    except Exception:
        pass

def deny(msg):
    if ROOT: log_block(ROOT, msg, CMD)
    sys.stderr.write(f"囤貨防線阻擋：{msg}。囤貨模式不允許此動作；改用其他方式，或記錄到 CATALOG.md「需要你決定的事」。\n")
    sys.exit(2)

def strip_heredocs(cmd):
    out, lines, i = [], cmd.split('\n'), 0
    while i < len(lines):
        line = lines[i]; out.append(line)
        m = re.search(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1", line)
        if m:
            tag = m.group(2); i += 1
            while i < len(lines) and lines[i].strip() != tag:
                i += 1
        i += 1
    return '\n'.join(out)

def mark_redirections(cmd):
    """Keep the distinction between syntax `>` and quoted text `'>'`."""
    out, quote, escaped, i = [], None, False, 0
    while i < len(cmd):
        char = cmd[i]
        if escaped:
            out.append(char); escaped = False
        elif char == '\\' and quote != "'":
            out.append(char); escaped = True
        elif quote:
            out.append(char)
            if char == quote: quote = None
        elif char in "'\"":
            quote = char; out.append(char)
        elif char == '>':
            fd = re.match(r'>&(\d+|-)', cmd[i:])
            if fd:
                out.append(" __JBI_OUT__ '&" + fd.group(1) + "' ")
                i += len(fd.group(0)) - 1
                i += 1
                continue
            append = i + 1 < len(cmd) and cmd[i + 1] == '>'
            out.append(' __JBI_APPEND__ ' if append else ' __JBI_OUT__ ')
            if append: i += 1
        else:
            out.append(char)
        i += 1
    return ''.join(out)


def segments(cmd):
    lex = shlex.shlex(mark_redirections(strip_heredocs(cmd)), posix=True, punctuation_chars=';&|<>()\n')
    lex.whitespace_split = True
    lex.whitespace = ' \t\r'
    lex.commenters = ''
    seg = []
    for tok in lex:
        if tok in (';', '&&', '||', '|', '&', '(', ')', '\n') or set(tok) <= set(';&|()'):
            if seg: yield seg
            seg = []
            for char in tok:
                if char in '()': yield [char]
        else:
            seg.append(tok)
    if seg: yield seg

def executable_name(path):
    # Git Bash may invoke the same utility through an absolute Windows path
    # or its explicit .exe filename. Neither form changes the policy.
    name = path.replace('\\', '/').rsplit('/', 1)[-1].casefold()
    return name[:-4] if name.endswith('.exe') else name


def unwrap(seg):
    # Wrappers must not hide the executable behind their own options.
    while seg:
        if re.match(r'^[A-Za-z_][A-Za-z0-9_]*=', seg[0]) or seg[0] in ('do', 'then', 'else', 'if', 'elif', 'while', 'until', '!', '{', '}'):
            seg = seg[1:]
            continue
        wrapper = executable_name(seg[0])
        if wrapper not in ('sudo', 'env', 'time', 'nohup', 'command', 'exec'):
            break
        seg = seg[1:]
        if wrapper == 'command' and seg and seg[0] in ('-v', '-V'):
            # Querying an executable does not run it. Keep all arguments so
            # the surrounding shell's redirections are still validated.
            return ['__JBI_COMMAND_QUERY__'] + seg
        while seg and seg[0].startswith('-'):
            option = seg[0]
            if option == '--':
                seg = seg[1:]
                break
            if ((wrapper == 'env' and option in ('-i', '--ignore-environment', '-0', '--null'))
                    or (wrapper == 'time' and option == '-p')):
                seg = seg[1:]
            elif wrapper == 'env' and option in ('-u', '--unset') and len(seg) >= 2:
                seg = seg[2:]
            elif wrapper == 'env' and option.startswith('--unset='):
                seg = seg[1:]
            else:
                deny('無法解析 wrapper 選項：' + wrapper + ' ' + option)
    return seg

def git_sub(seg):
    i = 1
    while i < len(seg) and seg[i].startswith('-'):
        i += 2 if seg[i] in ('-C', '-c') else 1
    return (seg[i], seg[i + 1:]) if i < len(seg) else (None, [])

def operands(args, value_options=()):
    """Skip options and their values, retaining file operands."""
    result, i, literal = [], 0, False
    while i < len(args):
        arg = args[i]
        if arg == '--' and not literal:
            literal = True
        elif not literal and arg in value_options:
            i += 1
        elif literal or not arg.startswith('-'):
            result.append(arg)
        i += 1
    return result


def check_target(target, cwd, recursive=False):
    if target in ('/dev/null', '/dev/stdout', '/dev/stderr') or re.fullmatch(r'&\d+', target):
        return
    try:
        reason = POLICY.check_write(target, cwd=cwd, recursive=recursive)
    except (PolicyError, OSError, ValueError) as error:
        deny(str(error))
    if reason:
        deny(reason)


def check_segment(seg, cwd, depth=0):
    seg = unwrap(seg)
    if not seg: return cwd
    w = executable_name(seg[0])

    # Redirection belongs to the surrounding shell, before a cd or wrapper.
    for i, arg in enumerate(seg):
        if arg in ('__JBI_OUT__', '__JBI_APPEND__'):
            if i + 1 >= len(seg): deny('缺少 shell 寫入目標')
            check_target(seg[i + 1], cwd)
    # Strip redirection tokens before interpreting command operands.
    clean, i = [], 0
    while i < len(seg):
        if seg[i] in ('__JBI_OUT__', '__JBI_APPEND__'):
            i += 2
        else:
            clean.append(seg[i]); i += 1
    seg = clean
    if not seg: return cwd
    w = executable_name(seg[0])
    if w in ('bash', 'sh', 'dash', 'zsh', 'ksh'):
        for i, arg in enumerate(seg[1:], 1):
            if arg.startswith('-') and not arg.startswith('--') and 'c' in arg[1:]:
                if i + 1 >= len(seg): deny('缺少 shell wrapper 指令')
                if depth >= 8: deny('shell wrapper 層數過多')
                check_command(seg[i + 1], cwd, depth + 1)
                return cwd
        if len(seg) > 1 and seg[1] in ('-s', '--stdin'):
            return cwd  # interpreter bodies are outside this blocklist's scope
    if w == 'cd':
        args = operands(seg[1:])
        if len(args) != 1 or re.search(r'[$`*?\[\]{}~]', args[0]):
            deny('無法解析 cd 目標')
        return os.path.realpath(os.path.join(cwd, args[0]))

    if w == 'git':
        sub, args = git_sub(seg)
        if sub == 'push':
            flags = [a for a in args if a.startswith('-')]
            pos = [a for a in args if not a.startswith('-')]
            if any(f in ('--force', '-f', '--force-with-lease', '--delete', '-d', '--mirror', '--all', '--tags') or f.startswith('--force') for f in flags):
                deny("git push 帶 force/delete/mirror")
            if len(pos) != 2 or ':' in pos[1] or not pos[1].startswith('hoard/'):
                deny("git push 只允許 `git push [-u] <remote> hoard/<…>`")
        elif sub in ('merge', 'rebase'):
            deny(f"git {sub}")
        elif sub == 'reset' and '--hard' in args:
            deny("git reset --hard")
        elif sub in ('checkout', 'switch') and args and args[-1] in ('main', 'master', 'develop') and not any(a in ('-b', '-c', '--create') for a in args):
            deny("切換到主分支")

    elif w == 'rm':
        flags = ''.join(a[1:] for a in seg[1:] if a.startswith('-') and not a.startswith('--'))
        if ('r' in flags or 'R' in flags or '--recursive' in seg) and ('f' in flags or '--force' in seg):
            deny("rm -rf")

    elif (w == 'dotnet' and seg[1:3] == ['add', 'package']) \
      or (w in ('npm', 'pnpm', 'yarn', 'bun') and len(seg) > 2 and seg[1] in ('install', 'i', 'add') and any(not a.startswith('-') for a in seg[2:])) \
      or (w in ('pip', 'pip3') and len(seg) > 1 and seg[1] == 'install') \
      or (w == 'nuget' and len(seg) > 1 and seg[1] == 'install'):
        deny("新增第三方套件")

    targets, recursive = [], False
    if w == 'sed' and any(a.startswith('-i') or a == '--in-place' or a.startswith('--in-place=') for a in seg[1:]):
        args = operands(seg[1:], ('-e', '--expression', '-f', '--file'))
        has_script_option = any(a in ('--expression', '--file') or a.startswith(('-e', '-f', '--expression=', '--file=')) for a in seg[1:])
        targets = args if has_script_option else args[1:]
    elif w in ('tee', 'truncate', 'touch', 'rm', 'rmdir', 'unlink', 'mkdir'):
        targets = operands(seg[1:], ('-s', '--size', '-r', '--reference', '-t', '-d', '--date', '-m', '--mode'))
        # rm -r/-R are switches, not options consuming the next filename.
        if w == 'rm': targets = operands(seg[1:])
        recursive = w in ('rm', 'rmdir')
    elif w in ('mv', 'cp', 'install'):
        args = operands(seg[1:], ('-t', '--target-directory', '-m', '--mode', '-o', '--owner', '-g', '--group'))
        target_dir = next((seg[i + 1] for i, a in enumerate(seg[:-1]) if a in ('-t', '--target-directory')), None)
        target_dir = next((a.split('=', 1)[1] for a in seg if a.startswith('--target-directory=')), target_dir)
        if target_dir:
            sources, destination = args, target_dir
        elif len(args) >= 2:
            sources, destination = args[:-1], args[-1]
        else:
            deny('無法解析 shell 複製／搬移目標')
        is_dir = os.path.isdir(os.path.join(cwd, destination)) or target_dir is not None or len(sources) > 1
        targets = [os.path.join(destination, os.path.basename(source)) for source in sources] if is_dir else [destination]
        if w == 'mv': targets += sources
        recursive = True
    elif w == 'perl' and any(a.startswith('-') and 'i' in a[1:] for a in seg[1:]):
        # Perl option combinations are too broad to resolve safely.
        deny('請用可檢查目標的檔案工具取代 perl 原地寫入')
    elif w == 'dd':
        targets = [a[3:] for a in seg[1:] if a.startswith('of=')]
    for target in targets:
        check_target(target, cwd, recursive)
    return cwd


def check_command(cmd, cwd, depth=0):
    try:
        parsed = list(segments(cmd))
    except ValueError:
        deny('shell 指令無法解析，無法驗證凍結邊界')
    groups = []
    for seg in parsed:
        if seg == ['(']:
            groups.append(cwd)
        elif seg == [')']:
            if groups: cwd = groups.pop()
        else:
            cwd = check_segment(seg, cwd, depth)

def main():
    root = project_root()
    if not os.path.isfile(os.path.join(root, '.hoard-pipeline', 'ACTIVE')):
        return
    try:
        ti = json.load(sys.stdin).get('tool_input', {})
        cmd = ti.get('command', '')
        if not isinstance(cmd, str): raise ValueError('command must be a string')
    except (ValueError, TypeError, AttributeError):
        deny('無法解析工具輸入')
    global ROOT, CMD, POLICY
    ROOT, CMD = root, cmd
    try:
        POLICY = PathPolicy(root)
    except (PolicyError, OSError, ValueError) as error:
        deny(str(error))
    cwd = ti.get('cwd') or ti.get('workdir') or root
    if not os.path.isabs(cwd): cwd = os.path.join(root, cwd)
    check_command(cmd, cwd)

if __name__ == '__main__':
    main()
