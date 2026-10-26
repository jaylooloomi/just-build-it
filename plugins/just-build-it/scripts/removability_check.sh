#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Arthur Wang
# 機械檢查「刪掉這個功能，其他測試會不會壞」。
# 用法：removability_check.sh <feature-dir>   需要 .hoard-pipeline/TEST_CMD
# 做法：把功能目錄暫時搬走 → 跑完整測試 → 搬回來。exit 0 = 可刪；exit 1 = 刪了會壞。
set -u
ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
P="$ROOT/.hoard-pipeline"
DIR="${1:?feature dir}"
[ -d "$ROOT/$DIR" ] || { echo "no such dir: $DIR"; exit 2; }
TEST_CMD="$(cat "$P/TEST_CMD" 2>/dev/null)"
[ -n "$TEST_CMD" ] || { echo "TEST_CMD missing in $P"; exit 2; }
TMP="$(mktemp -d)"
mv "$ROOT/$DIR" "$TMP/feat"
# 同時把 flag 註冊拿掉（flags.json 若存在），讓「刪除」更接近真實
FLAGS="$(dirname "$ROOT/$DIR")/flags.json"
SLUG="$(basename "$DIR")"
BK=""
if [ -f "$FLAGS" ]; then
  BK="$TMP/flags.json"; cp "$FLAGS" "$BK"
  python3 - "$FLAGS" "$SLUG" <<'PY' || true
import json,sys
p,slug=sys.argv[1],sys.argv[2]
d=json.load(open(p)); d.pop(slug,None); json.dump(d,open(p,'w'),ensure_ascii=False,indent=2)
PY
fi
( cd "$ROOT" && bash -c "$TEST_CMD" ) > "$P/removability-$SLUG.log" 2>&1
RC=$?
mv "$TMP/feat" "$ROOT/$DIR"
[ -n "$BK" ] && cp "$BK" "$FLAGS"
rm -rf "$TMP"
if [ $RC -eq 0 ]; then echo "REMOVABLE: $DIR（搬走後測試仍全綠）"; exit 0
else echo "NOT-REMOVABLE: $DIR（搬走後測試失敗，見 $P/removability-$SLUG.log）"; exit 1; fi
