#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Arthur Wang
"""Re-run coupling on the hoarded features. Called by the Stop hook every N turns.

Rule it enforces: features/<a>/ must not import features/<b>/. Cross-feature edges
mean the hoard is no longer independently deletable. Writes
.hoard-pipeline/coupling-warn.md (empty file = clean) and exits 0 always.
"""
import os, re, sys, json
sys.path.insert(0, os.path.dirname(__file__))
import preflight as pf

def main():
    root = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    feats = []
    for rel in pf.walk(root):
        m = re.search(r'(^|/)features/([^/]+)/', rel)
        if m and os.path.splitext(rel)[1] in pf.SRC_EXT:
            feats.append((rel, m.group(2)))
    stems = {os.path.splitext(f)[0]: f for f, _ in feats}
    bad = []
    for f, feat in feats:
        rx = pf.IMPORT_RE.get(os.path.splitext(f)[1])
        if not rx: continue
        for m in rx.findall(pf.read_text(root, f)):
            tgt = (m if isinstance(m, str) else next((x for x in m if x), '')).strip()
            mm = re.search(r'features/([^/]+)', tgt)
            if tgt.startswith('.'):
                cand = os.path.normpath(os.path.join(os.path.dirname(f), tgt)).replace(os.sep, '/')
                mm = re.search(r'(^|/)features/([^/]+)/', cand + '/')
                other = mm.group(2) if mm else None
            else:
                other = mm.group(1) if mm else None
            if other and other != feat:
                bad.append((f, feat, other))
    pd = os.path.join(root, '.hoard-pipeline'); os.makedirs(pd, exist_ok=True)
    out = os.path.join(pd, 'coupling-warn.md')
    with open(out, 'w', encoding='utf-8') as fh:
        if bad:
            fh.write('# 功能互相依賴（違反「可獨立刪除」）\n')
            for f, a, b in bad: fh.write(f'- `{f}`（{a}）引用了功能 {b}\n')
    print(json.dumps(dict(features=len(set(x for _, x in feats)), cross_edges=len(bad)), ensure_ascii=False))

if __name__ == '__main__':
    main()
