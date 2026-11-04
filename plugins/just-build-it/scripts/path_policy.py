#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Shared, canonical path policy for file tools and known shell write operations.

This is a guardrail, not a sandbox for arbitrary interpreters or scripts.
"""
import os
import re
import subprocess


class PolicyError(ValueError):
    pass


PROTECTED = re.compile(
    r'(^|/)(\.gitlab-ci\.yml|\.github/workflows(?:/.*)?|[Mm]igrations?(?:/.*)?'
    r'|appsettings[^/]*\.json|\.env[^/]*|web\.config|app\.config|[^/]*\.csproj'
    r'|package\.json|package-lock\.json|pnpm-lock\.yaml|yarn\.lock|bun\.lockb?'
    r'|requirements[^/]*\.txt|Directory\.Packages\.props)$', re.I)


def project_root():
    root = os.environ.get('CLAUDE_PROJECT_DIR')
    if root:
        return os.path.realpath(root)
    try:
        result = subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                                capture_output=True, text=True, timeout=5, check=True)
        return os.path.realpath(result.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        return os.path.realpath(os.getcwd())


def canonical(path):
    return os.path.normcase(os.path.realpath(path))


def load_frozen(root):
    """Load validated relative exact-file / trailing-slash-directory entries.

    Empty or comments-only files are valid: a measured project can have no
    frozen candidates. Missing, unreadable or malformed files are errors.
    """
    try:
        with open(os.path.join(root, '.hoard-pipeline', 'FROZEN'), encoding='utf-8') as stream:
            lines = stream.read().splitlines()
    except (OSError, UnicodeError) as error:
        raise PolicyError('FROZEN missing or unreadable') from error
    entries = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        normalized = line.replace('\\', '/')
        if ('\0' in normalized or re.search(r'[*?\[\]]', normalized)
                or normalized.startswith('/') or re.match(r'^[A-Za-z]:', normalized)
                or '..' in normalized.split('/') or normalized.rstrip('/') in ('', '.')):
            raise PolicyError('Invalid FROZEN entry: ' + line)
        normalized = os.path.normpath(normalized).replace('\\', '/')
        if line.endswith(('/', '\\')):
            normalized += '/'
        entries.append(normalized)
    return entries


def is_frozen(rel, frozen):
    rel = os.path.normcase(os.path.normpath(rel)).replace('\\', '/')
    for entry in frozen:
        entry = os.path.normcase(entry).replace('\\', '/')
        if rel == entry.rstrip('/') or (entry.endswith('/') and rel.startswith(entry)):
            return True
    return False


class PathPolicy:
    def __init__(self, root):
        self.root = canonical(root)
        self.frozen = load_frozen(self.root)
        self.frozen_absolute = [(canonical(os.path.join(self.root, entry)), entry.endswith('/'))
                                for entry in self.frozen]

    def check_write(self, path, cwd=None, recursive=False):
        if not isinstance(path, str) or not path or '\0' in path:
            raise PolicyError('Invalid write target')
        # A literal target cannot safely represent shell expansion.
        if re.search(r'[$`*?\[\]{}]', path) or path.startswith('~'):
            raise PolicyError('Cannot resolve shell write target: ' + path)
        # Git Bash commonly passes /c/... paths to Windows Python.
        if os.name == 'nt' and re.match(r'^/[A-Za-z]/', path):
            path = path[1] + ':' + path[2:]
        base = cwd or self.root
        lexical = os.path.abspath(os.path.join(base, path))
        absolute = canonical(lexical)
        for candidate in (lexical, absolute):
            rel = os.path.relpath(candidate, self.root).replace('\\', '/')
            if PROTECTED.search(rel):
                return '禁改清單：' + rel
        for frozen, directory in self.frozen_absolute:
            if (absolute == frozen or (directory and absolute.startswith(frozen + os.sep))
                    or (recursive and frozen.startswith(absolute.rstrip(os.sep) + os.sep))):
                return '核心凍結：' + path
        if recursive and os.path.isdir(absolute):
            # Removing/moving a parent directory must not remove protected
            # descendants (e.g. mv .github backup or rm -r a/config-dir).
            for parent, dirs, files in os.walk(absolute):
                dirs[:] = [name for name in dirs if name not in ('.git', 'node_modules', '.venv', 'venv', '__pycache__')]
                for name in dirs + files:
                    rel = os.path.relpath(os.path.join(parent, name), self.root).replace('\\', '/')
                    if PROTECTED.search(rel):
                        return '禁改清單：' + rel
        return None
