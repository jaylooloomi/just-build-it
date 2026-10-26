#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Arthur Wang
# Stop hook：囤貨進行中就把 Claude 推回去；沒有 ACTIVE 檔時完全不干擾。
# 三個階段：hoarding（囤） → packaging（最後 10% 時間，只打包不開新功能） → finishing（收工）。
# exit 0 = 允許停止；exit 2 + stderr = 阻止停止，stderr 內容是下一回合的指示。
set -u
ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
P="$ROOT/.hoard-pipeline"
S="$(dirname "$0")"

[ -f "$P/ACTIVE" ] || exit 0
python3 "$S/test_audit.py" "$ROOT" >/dev/null 2>&1 || true
[ -f "$P/DONE" ] && exit 0

HOURS="${HOARD_HOURS:-8}"
MAX_TURNS="${HOARD_MAX_TURNS:-300}"
PACK_PCT="${HOARD_PACK_PCT:-10}"        # 最後 N% 時間強制打包
PACK_MIN="${HOARD_PACK_MIN:-15}"        # 打包時間下限（分鐘）
AUDIT_EVERY="${HOARD_AUDIT_EVERY:-5}"   # 每 N 回合重跑耦合稽核

now=$(date +%s)
[ -f "$P/START" ] || echo "$now" > "$P/START"
[ -f "$P/DEADLINE" ] || echo $(( now + HOURS * 3600 )) > "$P/DEADLINE"
start=$(cat "$P/START"); deadline=$(cat "$P/DEADLINE")
total=$(( deadline - start )); remain=$(( deadline - now )); remain_min=$(( remain / 60 ))
pack_sec=$(( total * PACK_PCT / 100 )); [ $pack_sec -lt $(( PACK_MIN * 60 )) ] && pack_sec=$(( PACK_MIN * 60 ))
n=$(( $(cat "$P/turns" 2>/dev/null || echo 0) + 1 )); echo "$n" > "$P/turns"
base=$(cat "$P/BASE" 2>/dev/null || echo main)

finish() {
  cat >&2 <<MSG
囤貨結束條件已到（$1）。這是最後一回合，依 feature-hoarder skill Step 6 收工：
(1) 跑 core_check.sh；印出 git log --oneline ${base}..HEAD 與 git diff ${base} --name-only；
(2) 寫入 .hoard-pipeline/TIMING，補完 CATALOG.md（每個功能一張卡：一句話／怎麼開／怎麼刪／測試狀態）；
(3) git push -u origin hoard/<date>；(4) touch .hoard-pipeline/DONE && rm .hoard-pipeline/ACTIVE；
(5) 呼叫 catalog-reporter 子代理，把「報告老闆」原樣貼出。然後停止。
MSG
  echo finishing > "$P/STATE"; exit 2
}

[ -f "$P/STATE" ] && grep -q finishing "$P/STATE" && exit 0
[ -f "$P/STOP" ] && finish "使用者喊停 turns=$n"
[ "$now" -ge "$deadline" ] && finish "時間到 turns=$n"
[ "$n" -ge "$MAX_TURNS" ] && finish "回合用完 turns=$n"

# 週期耦合稽核（hook 做，不靠模型）
WARN=""
if [ $(( n % AUDIT_EVERY )) -eq 0 ]; then
  python3 "$S/coupling_audit.py" "$ROOT" >/dev/null 2>&1 || true
fi
[ -s "$P/coupling-warn.md" ] && WARN="⚠ 耦合稽核發現功能互相依賴（見 .hoard-pipeline/coupling-warn.md）：這違反「可獨立刪除」，本回合第一件事是解開或 revert 到合規點。"

# 打包階段：剩餘時間 ≤ 打包預留 → 不開新功能
if [ "$remain" -le "$pack_sec" ]; then
  echo packaging > "$P/STATE"
  cat >&2 <<MSG
進入打包階段（剩餘約 ${remain_min} 分鐘）。不准再開新功能。依 feature-hoarder skill Step 5：
- 正在做的功能：能在 10 分鐘內通過三題檢查就完成並 commit；否則 git stash 或 commit 加 [WIP-DROPPED] 並從 CATALOG.md 移除，不留半成品。
- 跑 core_check.sh；對每個功能跑 removability_check.sh，結果寫進 CATALOG.md。
- 確認 features/flags.json 全部預設 false、總開關面板／切換說明可用。
- 整理 CATALOG.md：人只看卡片不看 code；每張卡 ≤ 3 行＋一個開啟指令＋一個刪除指令。
- 印出 git status --short。打包完成就等 hook 宣布收工，不要自己 touch DONE。
${WARN}
MSG
  exit 2
fi

echo hoarding > "$P/STATE"
cat >&2 <<MSG
囤貨進行中（第 $n 回合；剩餘約 ${remain_min} 分鐘，最後 $(( pack_sec / 60 )) 分鐘會強制打包）。依 just-build-it:feature-hoarder skill 繼續：
- 從 candidates.md 取下一個候選（選擇器決定；清單用完就重新調研標竿痛點）。
- 一功能一目錄一 flag 一測試一卡片；commit 前跑三題檢查（core_check.sh／flag 關閉後測試全綠／removability_check.sh）。
- 每回合至少用一個工具，印出 git status --short 與測試結果。
- 完成即更新 CATALOG.md，然後立刻開下一個，不要停。
${WARN}
MSG
exit 2
