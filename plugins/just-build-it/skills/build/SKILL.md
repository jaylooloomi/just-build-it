---
name: build
description: Start a hoarding session — the agent grows independently removable features for N hours (default 8) and leaves a CATALOG.md to swipe through. Invoke explicitly as /just-build-it:build in Claude Code or $build in Codex.
argument-hint: "[hours] [--scope <dir>] [重點 X | focus on X | 只量 | measure only]"
disable-model-invocation: true
---
使用者不想上班。立刻依 feature-hoarder skill 開始，不要再問任何問題。

參數：$ARGUMENTS
（若上面那行沒有被替換成實際文字，參數就是使用者這則訊息裡 skill 名稱後面的文字。）

- 第一個 token 若是數字 = 執行時數（小時）；沒有就用 8。
- `--scope <目錄>`：強制區域模組模式，範圍就是該目錄。
- `重點 X` / `focus on X`：只調研與 X 有關的痛點。
- `只量` / `measure only`：跑完 Step 1（專案類型＋耦合度檢查）寫出 SCOPE.md 就收工。

Step 0 務必依時數寫入 .hoard-pipeline/DEADLINE（epoch 秒）；Step 1 務必先跑 scripts/preflight.py，模式由它的數字決定，不要用感覺判斷。
