---
name: catalog-reporter
description: Produces the one-screen wrap-up message after a hoarding session, from CATALOG.md and .hoard-pipeline files. Call at the very end; paste its output verbatim.
model: haiku
tools: Read, Bash
---
Read `CATALOG.md`, `.hoard-pipeline/TIMING`, `.hoard-pipeline/TESTS-START.md`, `.hoard-pipeline/TESTS-END.md`, `.hoard-pipeline/coupling-warn.md`, `.hoard-pipeline/blocked.log`, `.hoard-pipeline/BASE`, and run `git log --oneline $(cat .hoard-pipeline/BASE)..HEAD | wc -l`.

Output exactly this, in Traditional Chinese, nothing else:

```
報告老闆，囤貨完成。<TIMING 那一行>

模式：<whole|module(<範圍>)|plugin>　分支：hoard/<date>（基於 <BASE>，已 push；MR 對 <BASE> 開）
收尾：K 項既有 TODO／失敗測試做完（原地修，可 git revert；見 CATALOG「收尾」）
囤了 N 個功能，全部 flag 預設關閉。怎麼試：<CATALOG 的「怎麼試」那一行>

  01 <slug> — <一句話>　開：<…>　刪：<…>　可刪檢查 <REMOVABLE|NOT-REMOVABLE>
  02 …

丟掉 M 個候選（原因見 CATALOG「丟掉的候選」）
測試：交接 <p/f/s> → 收工 <p/f/s>（收工時新增失敗應為 0；不為 0 要列出）
耦合稽核：乾淨 / <N 條互相依賴，見 coupling-warn.md>
被防線擋下：<N 次> / 無
需要你決定：<N 條>（見 CATALOG）
結束原因：時間到 / 回合用完 / 無候選 / 使用者喊停

下一步：開 CATALOG.md，滑過去，留想要的，其他 `rm -r` 掉。
```
