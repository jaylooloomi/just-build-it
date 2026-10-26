#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Arthur Wang
# 機械檢查「核心有沒有被動」：本分支相對 BASE 的 diff ∩ FROZEN 必須為空。exit 0 = 乾淨。
set -u
ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
P="$ROOT/.hoard-pipeline"
BASE="$(cat "$P/BASE" 2>/dev/null || echo main)"
cd "$ROOT"
HIT=0
while IFS= read -r f; do
  [ -z "$f" ] && continue
  while IFS= read -r pat; do
    case "$pat" in ''|'#'*) continue;; esac
    if [ "${pat%/}" != "$pat" ]; then case "$f" in "$pat"*|"${pat%/}") HIT=1; echo "CORE-TOUCHED: $f（凍結：$pat）";; esac
    else [ "$f" = "$pat" ] && { HIT=1; echo "CORE-TOUCHED: $f"; }; fi
  done < "$P/FROZEN"
done < <(git diff "$BASE" --name-only)
[ $HIT -eq 0 ] && echo "CORE-CLEAN: 相對 $BASE 未動到任何凍結檔案"
exit $HIT
