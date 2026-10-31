# just-build-it 規格書

版本 0.1.0 ｜ 2026-10-31 ｜ 對應 repo：jaylooloomi/just-build-it

---

## 1. 核心目標

### 1.1 一句話

**在人給定的時限內，讓 AI 無人看管地持續產出「可獨立開關、可一鍵刪除、附一張卡」的功能，人只在事後做減法。**

### 1.2 三個子目標

| # | 目標 | 可量指標 |
|---|---|---|
| G1 | 不閒著 | 時限內每回合都有一個完整功能 commit 或一個明確 revert；無空轉回合 |
| G2 | 不弄髒 | 收工時：核心檔案 diff 為零、flag 全關測試全綠、每個功能搬走後測試仍綠、功能間零互引 |
| G3 | 人的減法成本趨近零 | 人只做三個動作：看卡、開 flag 試、`rm -r`；目標 20 分鐘內滑完整份 CATALOG |

### 1.3 非目標（明確不做）

- 不判斷功能是否值得做（價值判斷留給人）
- 不追求把產品「做對」或「做完」（那是 i-want-to-sleep）
- 不改既有核心程式碼（唯一例外：Step 2 掛載點，加法且一次）
- 不處理高耦合系統的核心（ERP、交易引擎 → 只碰擴充點）
- 不替人做減法

### 1.4 設計原則

| 原則 | 意思 |
|---|---|
| 紀律給腳本，判斷給模型 | 所有守門（核心未動、可刪、時限、禁寫）由腳本與 hook 強制；模型只負責理解、調研、寫碼 |
| 邊界錨，不要方向錨 | 不告訴它該往哪走，只告訴它哪裡不准碰；邊界是量出來的 |
| 加法靠想像，減法靠回饋 | AI 做加法，人做減法；兩者不混 |
| 完整樂高，不是零件 | 任何時刻 repo 內不存在未過檢查的半成品 |
| 模型升級自動變好，防線不變 | 可判斷的部分隨模型進步；可量的部分一行不改 |

---

## 2. 核心功能

| # | 功能 | 描述 | 實作 | 狀態 |
|---|---|---|---|---|
| F1 | 專案理解 | 讀 README/docs/ADR/CHANGELOG/入口檔/近 30 天 commit，寫一段專案目的；作為分類與調研依據 | `feature-hoarder` Step 1a；`preflight.py` 列必讀清單 | ✅ |
| F2 | 執行前量測 | 技術棧、產品型態、測試指令、依賴圖（扇入/扇出/循環）、TODO/FIXME、skip 測試 | `preflight.py` | ✅ |
| F3 | 模式判定 | whole / module / plugin 三模式，由數字決定；排除型態強制 module/plugin | `preflight.decide()` | ✅ |
| F4 | 核心凍結 | 扇入最高檔案＋模組對外介面寫入 FROZEN；write-guard 真的擋寫入 | `FROZEN`、`guard_write.py` | ✅ |
| F5 | 掛載點 | flag 讀取、功能註冊、總開關面板；整晚唯一一次碰核心 | Step 2（模型依技術棧實作） | ✅（形式由模型決定） |
| F6 | 收尾車道 | 範圍內、FROZEN 外的 TODO／失敗測試／skip 測試優先做完；一項一 commit；可 revert | Step 2b | ✅ |
| F7 | 痛點調研 | 以專案目的找 3 家同類產品，抓負評與 issue，候選必附來源 | Step 3 | ✅ |
| F8 | 候選挑選 | 去重、去需新套件者、同家族上限 3、分散掛載點；不評分 | `candidate-picker` agent | ✅ |
| F9 | 功能實作 | 一功能一目錄一 flag 一測試一卡片；≤5 檔、≤300 行淨增 | Step 5 | ✅ |
| F10 | 三題檢查 | 核心未動 / flag 關閉全綠 / 搬走仍綠；失敗 3 次 revert | `core_check.sh`、`TEST_CMD`、`removability_check.sh` | ✅ |
| F11 | 功能隔離稽核 | features/ 之間禁互引；每 5 回合 hook 重跑 | `coupling_audit.py` | ✅ |
| F12 | 三階段計時 | hoarding → packaging（剩 ≤10%，≥15 分鐘）→ finishing；由 hook 依 DEADLINE 切換 | `hoard-stop.sh` | ✅ |
| F13 | 證據協議 | 每回合須有工具呼叫、`git status --short`、三題檢查輸出；小模型查 transcript | prompt 型 Stop hook | ✅（Codex 不跑） |
| F14 | PreToolUse 防線 | 僅 `hoard/*` 分支；禁破壞性 git、裝套件、改 CI/migration/設定/依賴、寫 FROZEN | `guard_bash.py`、`guard_write.py` | ✅ |
| F15 | 測試稽核 | 偵測被刪、弱化、skip 的測試 | `test_audit.py` | ✅（繼承） |
| F16 | CATALOG | 功能卡（開/刪/來源/可刪結果/commit）、收尾段、丟棄候選、測試對照、耦合稽核、被擋動作、待決事項、統計 | Step 6 範本 | ✅ |
| F17 | 收工報告 | 一屏「報告老闆」 | `catalog-reporter` agent | ✅ |
| F18 | 雙平台 | Claude Code（`/just-build-it:build`）與 Codex（`$build`）同一套 hook 腳本 | `.claude-plugin/`、`.codex-plugin/` | ✅（Codex 未實戰） |

---

## 3. 流程規格

### 3.1 輸入

| 參數 | 型別 | 預設 | 說明 |
|---|---|---|---|
| hours | 數字 | 8 | 執行時數，寫入 DEADLINE |
| `--scope <dir>` | 路徑 | 無 | 強制 module 模式並指定範圍 |
| `重點 X` / `focus on X` | 文字 | 無 | 調研限定主題 |
| `只量` / `measure only` | 旗標 | 否 | 只跑 Step 0–1，寫 SCOPE.md 後收工 |

環境變數：`HOARD_HOT_RATIO`(0.08)、`HOARD_MAX_CYCLES`(2)、`HOARD_PACK_PCT`(10)、`HOARD_PACK_MIN`(15)、`HOARD_AUDIT_EVERY`(5)、`HOARD_MAX_TURNS`(300)。

### 3.2 狀態機

```
[idle] --/build--> [hoarding] --(remain ≤ pack_sec)--> [packaging] --(now ≥ DEADLINE | STOP | turns ≥ MAX)--> [finishing] --(DONE)--> [idle]
                       ^   |
                       └───┘  每回合：Stop hook 讀 DEADLINE，exit 2 推回
```

狀態存於 `.hoard-pipeline/STATE`；`ACTIVE` 存在且 `DONE` 不存在時 hook 才介入；`STOP` 檔觸發提前收工。

### 3.3 步驟規格

每步列：輸入 → 動作 → 輸出 → 離開條件 → 失敗處理 → 執行者。

**Step 0 開工**
- 輸入：hours、scope
- 動作：stash 未提交變更；記錄 BASE；`checkout -b hoard/<date>`；清空並建立 `.hoard-pipeline/`；寫 START、DEADLINE；touch ACTIVE
- 輸出：`.hoard-pipeline/{BASE,START,DEADLINE,ACTIVE}`
- 離開：DEADLINE 已寫（hook 依此運作）
- 執行者：模型

**Step 1a 理解專案**
- 輸入：`SCOPE.draft.md` 第 0 節的必讀清單
- 動作：讀文件、入口檔、近 30 天 commit；寫一段專案目的；與 preflight 的型態不一致時以理解為準修正
- 輸出：`SCOPE.md` 第 0 節
- 離開：專案目的非空
- 執行者：模型

**Step 1b 量測**
- 動作：`preflight.py <root> [--scope]`
- 輸出：`preflight.json`、`FROZEN`、`SCOPE.draft.md`
- 執行者：腳本

**Step 1c 定模式與邊界**
- 輸入：preflight 數字、Step 1a 理解
- 動作：依表決定模式；module 模式挑選模組（TODO 密度／issue／commit 頻率最高者，非最乾淨者）並把對外介面加入 FROZEN；plugin 模式把既有 src 全部加入 FROZEN；決定 TEST_CMD 並跑一次
- 輸出：`SCOPE.md`、`TEST_CMD`、`TESTS-START.md`
- 失敗：找不到可跑測試 → 收尾車道首項改為「建立測試基礎」
- 執行者：模型（數字來自腳本）

| preflight 判定 | 條件 | 模式 |
|---|---|---|
| 排除型態（ERP/交易/帳務） | 關鍵字命中且理解確認 | plugin（有擴充點）/ module |
| hot_ratio > 0.08 或 cycles > 2 | 高耦合 | plugin（有擴充點）/ module |
| 無測試 | — | module |
| 低耦合且有測試 | — | whole |
| 使用者 `--scope` | — | module（覆寫） |

**Step 1d 邊界複核**
- 動作：`scope-finalizer` 六項檢查（模式一致、FROZEN 涵蓋介面、落點在範圍、TEST_CMD 可跑、FROZEN 無 glob）
- 輸出：`VERDICT: OK | ISSUES`
- 失敗：ISSUES → 修 SCOPE/FROZEN 後重跑
- 執行者：小模型

**Step 2 掛載點**
- 動作：`isEnabled(slug)` 讀 `features/flags.json`；掛載機制（路由/指令/事件/遊戲物件/middleware，依技術棧選一）；總開關面板；跑測試；commit；掛載點檔案加入 FROZEN
- 約束：只新增註冊點，不改既有行為；本步是整晚唯一碰核心的一次
- 輸出：`features/flags.json`（`{}`）、`CATALOG.md` 骨架、commit `feat(hoard): mount point + flag registry`
- 執行者：模型

**Step 2b 收尾車道**
- 輸入：`SCOPE.md` 第 2b 節
- 動作：挑具體可驗證項目（範圍內、FROZEN 外），依檔案順序最多 10 項；每項：修 → `core_check.sh` → 完整測試 → commit `fix(hoard/wrap-NN)` → 寫 CATALOG「收尾」
- 約束：不得弱化斷言或加 skip（test_audit 偵測）
- 失敗：3 次不過 → revert，記錄卡點；FROZEN 內 TODO → 列待決不做
- 離開：清單處理完或無可做項
- 執行者：模型，腳本把關

**Step 3 調研**
- 輸入：`SCOPE.md` 第 0 節專案目的、`重點 X`
- 動作：找 3 家同類產品；抓負評/issue/抱怨串；每候選寫「使用者抱怨 X（來源）→ 本專案功能 Y → 掛載點 Z」
- 約束：無來源不收；需新套件不收；GPL/AGPL 不搬；抄行為不抄程式碼
- 輸出：`candidates.md`（8–20 個）
- 執行者：模型

**Step 4 挑選**
- 輸入：candidates.md、recent-commits.md、CATALOG.md、SCOPE.md
- 動作：`candidate-picker` 依序：無來源 → 與既有 commit/卡重複 → 需新套件 → 同家族已達 3 → 剩餘者挑掛載點最少的；>5 檔/300 行者標 SLICE
- 輸出：`PICK: n | none`
- 失敗：none → 回 Step 3；連續兩次 none → touch STOP
- 執行者：小模型

**Step 5 實作**
- 動作：建 `features/<NN-slug>/`；註冊 flag=false；功能內部僅在 isEnabled 為真時掛上；寫功能測試；寫卡片（≤3 行＋截圖/輸出至 `.hoard-pipeline/cards/`）
- 約束：只引用核心與掛載點，不引用其他 features；≤5 檔、≤300 行淨增
- 執行者：模型

**Step 5′ 三題檢查**（commit 前，輸出須留在 transcript）

| 題 | 指令 | 通過條件 |
|---|---|---|
| Q1 核心沒動？ | `core_check.sh` | `git diff BASE --name-only` ∩ FROZEN = ∅ |
| Q2 flag 關閉全綠？ | `bash -c "$(cat TEST_CMD)"` | 完整測試 exit 0 |
| Q2′ flag 開啟功能測試綠？ | 臨時改 true 跑功能測試後改回 | exit 0 |
| Q3 刪掉不壞？ | `removability_check.sh <dir>` | 搬走目錄＋移除 flag → 測試 exit 0 → 搬回 |

- 失敗：修；3 次仍失敗 → `git checkout -- . && git clean -fd <dir>`，候選標 `[DROPPED]`
- 通過：commit `feat(hoard/NN-slug): <一句話>`；更新 CATALOG；回 Step 4
- 執行者：腳本

**迴圈控制（Stop hook，每回合）**
- 若 `DONE` 存在或無 `ACTIVE` → exit 0（不干擾）
- 若 `STOP` 存在 / now ≥ DEADLINE / turns ≥ MAX → 寫 STATE=finishing，exit 2 並送收工指示
- 若 remain ≤ max(total×10%, 15min) → STATE=packaging，exit 2 並送打包指示
- 否則 STATE=hoarding，exit 2 並送繼續指示；每 5 回合先跑 `coupling_audit.py`，有互引則附警告
- 另：prompt 型 hook 檢查上一回合證據（工具呼叫、git status、三題輸出）；缺則 exit 2 指出缺項

**Step 6 打包**（STATE=packaging）
- 動作：不開新功能；手上功能 10 分鐘內過三題則 commit，否則 revert 並從 CATALOG 移除；跑 `core_check.sh`；對每功能跑 `removability_check.sh` 寫入卡片；確認 flags 全 false、面板可用；整理 CATALOG
- 離開：等 hook 宣布 finishing（不自行 touch DONE）
- 執行者：模型

**Step 7 收工**（STATE=finishing）
- 動作：寫 TIMING；完整測試 → `TESTS-END.md`；`core_check.sh`；`git log BASE..HEAD`、`git diff BASE --name-only`；補完 CATALOG；commit `docs(hoard): catalog`；`git push -u origin hoard/<date>`；touch DONE、rm ACTIVE；`catalog-reporter` 產生報告並原樣貼出
- 輸出：`CATALOG.md`、遠端分支、報告
- 執行者：模型＋腳本＋小模型

### 3.4 產出物規格

**`CATALOG.md`** 必含段落：標頭（模式/分支/BASE/功能數/flag 狀態/怎麼試）→ 收尾表 → 功能卡表（#/slug/一句話/開啟/刪除/來源/測試/可刪檢查/commit）→ 丟掉的候選 → 測試對照（交接/收工）→ 耦合稽核 → 被防線擋下 → 需要你決定 → 統計。

**`.hoard-pipeline/`** 檔案：

| 檔 | 寫入者 | 用途 |
|---|---|---|
| ACTIVE / DONE / STOP | 模型 / 模型 / 人或模型 | 狀態旗標 |
| BASE / START / DEADLINE / STATE / turns | 模型 / hook | 計時與狀態 |
| preflight.json / FROZEN / SCOPE.draft.md | preflight.py | 量測結果 |
| SCOPE.md / TEST_CMD | 模型 | 定稿邊界 |
| candidates.md / recent-commits.md | 模型 | 調研 |
| TESTS-START.md / TESTS-END.md / test-audit.md | 模型 / test_audit.py | 測試對照 |
| coupling-warn.md | coupling_audit.py | 互引警告 |
| blocked.log | guards | 被擋動作 |
| removability-<slug>.log | removability_check.sh | 可刪檢查記錄 |
| cards/ | 模型 | 截圖/輸出 |
| TIMING | 模型 | 時間統計 |

### 3.5 防線規格（PreToolUse，exit 2 阻擋）

| 類別 | 規則 |
|---|---|
| Git | 僅 `hoard/*`；禁 merge/rebase/reset --hard/--force/切主分支；push 僅至 hoard/* |
| 核心凍結 | FROZEN 內路徑禁寫（Step 2 例外，完成即凍結） |
| 禁改清單 | CI、migration、`appsettings*`/`*.config`/`.env*`、`*.csproj`/`package.json`/lock/`requirements*` |
| 依賴 | 禁安裝第三方套件 |
| 規模 | 單功能 ≤5 檔、≤300 行淨增（模型自律，picker 標 SLICE） |
| 隔離 | features/ 間禁互引（hook 稽核） |
| 半成品 | packaging/finishing 階段不得存在未過三題的功能 |

### 3.6 提前結束

`/just-build-it:stop`、口語「停」、或 `touch .hoard-pipeline/STOP` → 不開新功能；手上功能過三題則留、否則 revert；進 Step 7，結束原因「使用者喊停」。`stop 立刻/now` → 手上功能直接 revert。

---

## 4. 驗收標準（第一次實戰）

| 項目 | 通過條件 |
|---|---|
| 量測 | `只量` 對你的 repo 判定模式合理；FROZEN 清單人工看過無明顯漏 |
| 不弄髒 | 收工時 `core_check.sh` CLEAN；TESTS-END 失敗數 ≤ TESTS-START；coupling-warn.md 為空 |
| 不閒著 | 回合數 ≈ 功能數 ＋ 丟棄數 ＋ 收尾數（無空轉） |
| 可刪 | 隨機抽 3 個功能 `rm -r`＋刪 flag，測試全綠 |
| 減法成本 | 人滑完 CATALOG ≤ 20 分鐘 |
| 半成品 | 分支上無 `[WIP]` commit、CATALOG 無未過檢查項 |

---

## 5. 已知風險與未決

| 風險 | 說明 | 緩解 |
|---|---|---|
| 耦合門檻未校準 | 0.08 / 2 是估值 | 先用 `--scope` 跑 module 模式；跑數個 repo 後調 |
| 掛載點出錯 | Step 2 由模型設計，是唯一碰核心處 | 第一次跑人工審該 commit |
| 同質功能 | 低垂果實過多 | 同家族上限 3；可降 |
| Codex 未實戰 | 證據 hook 不跑 | 前幾回合人工盯 |
| 收尾上限 10 項 | 舊專案 TODO 多 | 可調 SKILL.md 該行 |
| 混合型 repo 判定模糊 | 前後端同 repo | 使用者給 `--scope` |
