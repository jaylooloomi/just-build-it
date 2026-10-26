---
name: stop
description: End a running hoarding session early — finish or revert the current feature, package the catalog, report. Invoke explicitly as /just-build-it:stop in Claude Code or $stop in Codex.
argument-hint: "[立刻 | now]"
disable-model-invocation: true
---
使用者要提前結束囤貨。依 feature-hoarder skill 的「提前結束」規則執行，不要問問題。

參數：$ARGUMENTS

- 沒有參數：`touch .hoard-pipeline/STOP`；手上的功能做完三題檢查就 commit，過不了就 revert；然後 Step 6 收工。
- 含「立刻」「now」或「immediately」：`touch .hoard-pipeline/STOP`；手上的功能直接 revert（不留半成品，從 CATALOG 移除）；立即 Step 6 收工。

結束原因寫「使用者喊停」。
