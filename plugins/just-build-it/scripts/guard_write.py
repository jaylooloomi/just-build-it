#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Arthur Wang
"""PreToolUse file/patch guard using the same path policy as the shell guard."""
import json
import os
import re
import sys
from path_policy import PathPolicy, PolicyError, project_root

PATCH_HDR = re.compile(r'^\*\*\* (?:Add|Update|Delete) File: (.+)$|^\*\*\* Move to: (.+)$', re.M)


def log_block(root, rule, detail):
    try:
        import datetime
        line = detail.replace('\n', ' ⏎ ')[:300]
        with open(os.path.join(root, '.hoard-pipeline', 'blocked.log'), 'a', encoding='utf-8') as stream:
            stream.write(f'{datetime.datetime.now():%Y-%m-%d %H:%M:%S}\t{rule}\t{line}\n')
    except OSError:
        pass


def deny(root, message, detail=''):
    log_block(root, message, detail)
    sys.stderr.write(f'囤貨防線阻擋：{message}。請記錄到 CATALOG.md「需要你決定的事」。\n')
    sys.exit(2)


def main():
    root = project_root()
    if not os.path.isfile(os.path.join(root, '.hoard-pipeline', 'ACTIVE')):
        return
    try:
        ti = json.load(sys.stdin).get('tool_input', {}) or {}
        if not isinstance(ti, dict):
            raise ValueError('tool_input must be an object')
    except (ValueError, TypeError, AttributeError):
        deny(root, '無法解析工具輸入')
    paths = [ti[key] for key in ('file_path', 'path') if isinstance(ti.get(key), str)]
    cmd = ti.get('command') if isinstance(ti.get('command'), str) else ''
    paths += [(a or b).strip() for a, b in PATCH_HDR.findall(cmd)]
    if not paths:
        deny(root, '找不到寫入目標')
    try:
        policy = PathPolicy(root)
        for path in paths:
            reason = policy.check_write(path)
            if reason:
                deny(root, reason, path)
    except (PolicyError, OSError, ValueError) as error:
        deny(root, str(error))


if __name__ == '__main__':
    main()
