---
name: feature-hoarder
description: 定時囤貨機。當使用者說「我不想上班」「幫我囤功能」「自己長功能 N 小時」「hoard」「evolve」或下 /hoard [hours] 指令時，一定要使用此技能。它先量專案類型與耦合度決定模式（全專案／區域模組／外掛），再在時限內無限迴圈地新增「可獨立開關、可一鍵刪除、附一張卡」的功能，最後 10% 時間強制打包成 CATALOG.md，讓使用者隔天用拇指做減法。沒有方向錨、不評價功能好壞；紀律由腳本強制，判斷留給人。
---

# Feature Hoarder：量 → 囤 → 打包 → 人來減

## 定位（跟 i-want-to-sleep 的差別）

| | i-want-to-sleep | just-build-it |
|---|---|---|
| 錨 | 對話裡的原始需求 | **沒有方向錨，只有邊界錨**（SCOPE.md / FROZEN） |
| 目標 | 把承諾的事做完、再加分 | **不要閒著**：在時限內囤最多「可拆卸」的功能 |
| 誰判斷值不值得 | scorer 子代理 | **沒有人判斷**。選擇器只做去重與分散，價值判斷留給使用者隔天 |
| 守門 | 分數門檻 | **三題機械檢查**：核心沒動？flag 關掉全綠？刪掉不壞？ |
| 結束 | 時間到 | 時間到，但**最後 10% 強制打包**，不留半成品 |

你不需要自己維持迴圈：只要 `.hoard-pipeline/ACTIVE` 存在且 `DONE` 不存在，Stop hook 會在你每次想停下時把你推回來，並在最後 10% 時間把你切到打包階段。

## 執行環境

- 子代理 `scope-finalizer`、`candidate-picker`、`catalog-reporter` 是 Claude Code 子代理；Codex 等環境改用平行 agent 功能把 `agents/*.md` 當指示交給它，沒有子代理就自己另開獨立步驟照做並在 CATALOG.md 註明。
- 指令：Claude Code `/just-build-it:go`、`/just-build-it:stop`；Codex `$go`、`$stop`。
- 腳本都在 `${CLAUDE_PLUGIN_ROOT}/scripts/`，下文簡寫為 `scripts/`。

## 執行順序

### Step 0 — 開分支、立旗標

```bash
git status --porcelain | grep -q . && git stash push -m "hoard pre-stash"
BASE=$(git branch --show-current)
git checkout -b hoard/$(date +%Y-%m-%d)
rm -rf .hoard-pipeline && mkdir -p .hoard-pipeline
echo "$BASE" > .hoard-pipeline/BASE
touch .hoard-pipeline/ACTIVE
HOURS=<來自 /go 參數，預設 8>
date +%s > .hoard-pipeline/START
echo $(( $(date +%s) + HOURS * 3600 )) > .hoard-pipeline/DEADLINE
```

- DEADLINE 是 hook 判斷打包與收工的唯一依據，寫錯整晚不會停。
- 整晚只在 `hoard/*` 分支。禁 merge / rebase / reset --hard / --force；push 只在收工時推到這條分支。

### Step 1 — 執行前檢查（先類型、後耦合，都是量出來的）

```bash
python3 scripts/preflight.py "$PWD" [--scope <使用者指定的子目錄>]
cat .hoard-pipeline/SCOPE.draft.md
```

preflight 會寫出三個檔：`preflight.json`（數字）、`FROZEN`（扇入最高的檔案 = 核心凍結清單，write-guard 會真的擋）、`SCOPE.draft.md`。

然後決定測試指令並寫入 `.hoard-pipeline/TEST_CMD`（preflight 猜不到就自己找；**找不到可跑的測試 → 前幾個功能必須是「補測試」**，否則三題檢查無法執行）。跑一次完整測試寫入 `.hoard-pipeline/TESTS-START.md`（指令、通過／失敗／略過數、失敗名稱）。

**模式對應動作**：

| preflight 判定 | 你要做的事 |
|---|---|
| `whole` | 直接用 SCOPE.draft.md，功能落在 `features/` |
| `module` | 使用者有 `--scope X` → 範圍就是 X。沒有 → 從 SCOPE 第 5 節列出 3 個候選模組，**挑 TODO/FIXME 密度、issue 提及、近 30 天 commit 數最高的（痛點最多），不是最乾淨的**；把該模組的對外介面（public API、export、controller 簽章）加進 FROZEN；功能落在 `<模組>/features/` |
| `plugin` | 不碰 repo 既有程式碼：所有功能寫在擴充點（plugins/、extensions/、middleware 註冊）；FROZEN 加入整個既有 src 目錄 |

把定稿寫到 `.hoard-pipeline/SCOPE.md`，交給 `just-build-it:scope-finalizer` 子代理複核（它只檢查：FROZEN 是否涵蓋對外介面、功能落點是否在範圍內、TEST_CMD 是否真的能跑）。`VERDICT: ISSUES` 就照它的指出修。

建立 `features/flags.json`（`{}`）和 `CATALOG.md` 骨架（格式見 Step 6）。commit：`chore(hoard): scope + preflight`。

### Step 2 — 建最小可掛載點（只做一次）

功能要「掛」在核心上而不是「改」核心，所以需要一個掛載機制。依技術棧做一個最小版本，**這是整晚唯一可以碰既有程式碼的一次**，且只能是加法（新增註冊點），不能改既有行為：

- flag 讀取：一個函式讀 `features/flags.json`，`isEnabled(slug)`，預設 false。
- 掛載：依型態選一個（路由表註冊 / 指令註冊 / 事件 hook / 遊戲物件註冊 / middleware 串），功能透過它進入，核心不知道功能存在。
- 總開關面板：能顯示所有功能與開關狀態的最小介面（web 就是 `/features` 頁；CLI 就是 `--features` 列表；遊戲就是 debug menu）。這是使用者隔天「試一下」的入口。

掛載點做完跑測試，commit：`feat(hoard): mount point + flag registry`。之後把掛載點檔案加進 FROZEN。

### Step 3 — 調研候選（抓痛點，不抓功能表）

```bash
git log --since=30.days --oneline > .hoard-pipeline/recent-commits.md
```

以 SCOPE.md 第 1 節的產品型態為線索，找 3 家最大的同類產品／開源專案。**抓它們的負評、GitHub issues、Reddit 抱怨串，不抓功能列表**。產出 8–20 個候選寫進 `.hoard-pipeline/candidates.md`，每個候選這個句型：

> 同類產品的使用者抱怨 **X**（來源：連結）；在本專案可以做成一個獨立功能 **Y**，掛在 **Z** 掛載點。

- 沒有來源的候選不收（這是迴圈裡唯一不是你自己產生的訊號）。
- 需要新增第三方套件 → 不收，寫進 CATALOG.md「需要你決定的事」。
- 抄的是行為與設計，不是程式碼、UI 素材、文案；GPL/AGPL 一律不搬。

### Step 4 — 挑一個（選擇器不評價好壞）

把 candidates.md、recent-commits.md、CATALOG.md 交給 `just-build-it:candidate-picker` 子代理。它**不打價值分**，只做三件事：剔除與既有 commit／既有功能重複的、剔除同質的（已有 3 個「匯出成 X 格式」就不准第 4 個）、在剩下的裡面挑掛載點最分散的。回傳 `PICK: <#>`。

- 採用它的 PICK。你唯一可覆寫的方向是往下跳（違反 FROZEN／規模）。
- 單一功能 ≤ 5 檔、≤ 300 行淨增；超過就切片，只做第一片。
- `PICK: none` → 回 Step 3 重新調研；連續兩輪 none → touch STOP 要求收工。

### Step 5 — 實作一個功能（三條紀律＋三題檢查）

**三條紀律**（違反任一條就不算功能）：

1. **可開關**：全部程式碼在 `<範圍>/features/<NN-slug>/`（NN 從 01 遞增）；`flags.json` 註冊 `"<NN-slug>": false`；功能內部只在 `isEnabled` 為真時掛上。
2. **可刪除**：只引用核心與掛載點，**不引用其他 features/**；核心與其他功能不引用它。刪除 = 刪目錄＋刪 flag 一行。
3. **有卡片**：CATALOG.md 一張卡 ≤ 3 行：一句話做什麼、怎麼開（指令或 toggle）、怎麼刪；附截圖/輸出範例路徑（存 `.hoard-pipeline/cards/<NN-slug>.*`）。

寫 code ＋ 功能自己的測試（放功能目錄內）。然後 **commit 前必跑三題檢查，輸出要留在 transcript**（證據 hook 會查）：

```bash
bash scripts/core_check.sh                                  # Q1 核心有沒有被動？
python3 - <<'PY'                                             # Q2 flag 關閉時全綠？（預設就是關閉）
import json;print(json.load(open('features/flags.json')))
PY
bash -c "$(cat .hoard-pipeline/TEST_CMD)"                    #    完整測試，必須全綠
bash scripts/removability_check.sh <範圍>/features/<NN-slug>   # Q3 刪掉會不會壞？
```

- 三題任一失敗 → 修；重試 3 次仍失敗 → `git checkout -- . && git clean -fd <功能目錄>` revert 掉，候選標 `[DROPPED]` 寫一行原因，進下一個。**不留半成品，不做 `[WIP-FAILED]`。**
- 也要跑一次 flag 開啟的測試（臨時把 flag 改 true 跑功能自己的測試，跑完改回 false）。
- commit：`feat(hoard/NN-slug): <一句話>`。一功能一 commit，不混。
- commit 後立刻更新 CATALOG.md，然後回 Step 4 取下一個。**不停。**

**打包階段**（hook 宣布「進入打包階段」後）：不開新功能；手上的功能 10 分鐘內過不了三題就 revert 並從 CATALOG 移除；對每個功能重跑 removability_check.sh 把結果寫進卡片；確認 flags.json 全部 false、總開關面板可用；整理 CATALOG.md。

### Step 6 — 收工：CATALOG.md ＋ 報告

hook 宣布收工後：

0. 寫 TIMING：
   ```bash
   python3 -c "import time;P='.hoard-pipeline/';s=int(open(P+'START').read());d=int(open(P+'DEADLINE').read());e=int(time.time());f=lambda t:time.strftime('%Y-%m-%d %H:%M',time.localtime(t));h=lambda x:f'{x//3600}h{x%3600//60:02d}m';open(P+'TIMING','w').write(f'開始 {f(s)}｜結束 {f(e)}｜實際 {h(e-s)}／預定 {h(d-s)}\n')"
   ```
1. 用 TEST_CMD 再跑一次完整測試寫 `TESTS-END.md`；跑 `core_check.sh`；印 `git log --oneline $BASE..HEAD`、`git diff $BASE --name-only`。
2. 補完 CATALOG.md；commit `docs(hoard): catalog`；`git push -u origin hoard/<date>`。
3. `touch .hoard-pipeline/DONE && rm .hoard-pipeline/ACTIVE`。
4. 呼叫 `just-build-it:catalog-reporter`，把回傳的報告原樣貼出，然後停止。

```markdown
# CATALOG（YYYY-MM-DD）— 滑過去、開一下、不要就刪

模式：whole / module(<範圍>) / plugin ｜ 分支 hoard/<date> 基於 <BASE> ｜ 功能數 N ｜ 全部 flag 預設關閉
怎麼試：<總開關面板的開法，一行>

## 功能卡（每張可獨立開關、獨立刪除）
| # | slug | 一句話 | 開啟 | 刪除 | 來源痛點 | 測試 | 可刪檢查 | commit |
|---|---|---|---|---|---|---|---|---|
| 01 | 01-xxx | … | flags.json 改 true | `rm -r features/01-xxx` ＋刪 flag 行 | <連結> | ✅ | REMOVABLE | abc123 |

## 丟掉的候選
- （slug / 原因：三題哪一題過不了、同質、重複）

## 測試對照
| | 通過 | 失敗 | 略過 |
|---|---|---|---|
| 交接時 | | | |
| 收工時 | | | |
測試稽核：原樣貼 `.hoard-pipeline/test-audit.md`。

## 耦合稽核
原樣貼 `.hoard-pipeline/coupling-warn.md`（空＝乾淨）。

## 被防線擋下的動作
原樣對應 `.hoard-pipeline/blocked.log`，每行補意圖與處理。

## 需要你決定的事
- （stash 的變更、需要新套件的候選、module 模式挑選的模組與理由）

## 統計
回合數、功能數、丟棄數、commit 數、淨增行數、結束原因（時間到／回合用完／無候選／喊停）
```

CATALOG.md 從 Step 1 起就要存在並隨做隨更新——context 可能被壓縮，檔案是唯一可靠記憶。

## 提前結束

`/just-build-it:stop`、「停」「先到這裡」「stop」、或從別的終端機 `touch .hoard-pipeline/STOP`：不開新功能；手上的做完三題就 commit，否則 revert；執行 Step 6。結束原因寫「使用者喊停」。

## 每回合必做（證據協議）

每回合結束前印 `git status --short`；有測試就印摘要；commit 功能前 transcript 裡必須有 core_check.sh 與 removability_check.sh 的輸出。證據 hook 只指出缺哪一樣，被擋就補，不辯解。

## 硬性圍欄

| 類別 | 規則（hook 真的會擋） |
|---|---|
| Git | 只在 `hoard/*`；push 只到該分支；禁 merge / rebase / reset --hard / --force / 切主分支 |
| 核心凍結 | `.hoard-pipeline/FROZEN` 內的路徑禁寫（Step 2 掛載點那一次例外，做完就加進 FROZEN） |
| 禁改清單 | CI、migration、`appsettings*`/`*.config`/`.env*`、`*.csproj`/`package.json`/lock/`requirements*` |
| 依賴 | 禁新增第三方套件 |
| 規模 | 單功能 ≤ 5 檔、≤ 300 行淨增 |
| 功能隔離 | features/ 之間禁互引（hook 每 5 回合稽核） |
| 半成品 | 打包階段與收工時不得存在未過三題的功能 |

## /go 參數

- `<數字>`：時數，預設 8。
- `--scope <目錄>`：強制 module 模式並指定範圍（**建議每次都給**；不給時 agent 會自己挑痛點最多的模組，但它可能挑錯）。
- `重點 X`：Step 3 只調研與 X 有關的痛點。
- `只量`：只跑 Step 1 寫出 SCOPE.md 就收工（用來先看它會怎麼判定）。

## 不要做的事

- 不判斷功能值不值得、不打價值分——那是使用者隔天的事。
- 不改核心、不改其他功能；守不住就 revert，不硬掰。
- 不留 `[WIP]`。囤的是完整樂高，不是零件。
- 不為了「看起來專業」加 CI、Docker、badge。
- 不讀前幾次的 `.hoard-pipeline/`。
- 不在做完一個功能後停下——除非 hook 要你打包或收工。
