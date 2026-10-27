<h1 align="center">just-build-it 🔨 做就對了</h1>

<p align="center">
  <b>人就是不想上班。</b><br>
  輸入 <code>/build 8 --scope src/reports</code>，去做別的事。回來：一箱可獨立開關、可一鍵刪除的功能。滑過去，留想要的，其他刪掉。
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="license MIT"></a>
  <img src="https://img.shields.io/badge/version-0.1.0-informational" alt="version 0.1.0">
  <img src="https://img.shields.io/badge/platform-macOS%20%7C%20Linux%20%7C%20WSL-lightgrey" alt="platform macOS | Linux | WSL">
  <img src="https://img.shields.io/badge/Python-3.8%2B-3776AB" alt="Python 3.8+">
  <img src="https://img.shields.io/badge/Claude%20Code-plugin-D97757" alt="Claude Code plugin">
  <img src="https://img.shields.io/badge/Codex-plugin-black" alt="Codex plugin">
  <a href="tests"><img src="https://img.shields.io/badge/tests-11%20passing-brightgreen" alt="tests 11 passing"></a>
  <a href="README.md"><img src="https://img.shields.io/badge/lang-English-green" alt="English"></a>
</p>

## 核心理念

**全程交給 AI，人不介入；人只在事後做減法。**

| 誰 | 做什麼 | 什麼時候 |
|---|---|---|
| AI | 理解專案、量邊界、調研、一個接一個做功能、自我檢查、打包 | 時限內全部，無人看管 |
| 人 | 滑 CATALOG：留想要的、刪不要的 | 事後，20 分鐘 |

AI 不判斷哪個功能值得做——它做很多個、每個都可以一鍵刪掉。判斷交給用過之後的人。這就是為什麼它不需要你先寫規格，也不會中途問你問題。

## 使用情境

| 情境 | 怎麼下 | 為什麼適合 |
|---|---|---|
| 🛋️ **週末、長假** | `/build 24 --scope src/game` | 不用交代要做什麼。它自己抓同類產品的使用者抱怨，一個一個做成可開關的功能 |
| 💳 **訂閱額度快重置還沒用完** | `/build 3 --scope <任一模組>` | 額度歸零前把它燒成功能庫存 |
| 🧪 **先看它會怎麼判定我的 repo** | `/build 只量` | 只跑執行前檢查，寫出 SCOPE.md 就停——看耦合度數字和它選的模式，再決定給不給它跑 |
| 🔍 **想知道競品使用者在抱怨什麼** | `/build 2 重點 匯出與報表` | 調研步驟抓的是負評和 issue，不是功能表 |
| 🏚️ **舊系統、高耦合、不敢動** | `/build 8`（它會自己判成 module 或 plugin 模式） | 核心凍結清單由腳本量出、hook 真的擋寫入；功能只能掛上去，不能改核心 |
| 🌙 **夜間交班、要把對話裡的事做完** | ❌ 用 [i-want-to-sleep](https://github.com/jaylooloomi/i-want-to-sleep) | 那是「做對一件事」；這個是「不要閒著」。兩個可以同時裝 |

Codex 上改用 `$build`：`$build 3 --scope src/api`。

## 安裝

**需求：** Claude Code ≥ 2.1.139 或 Codex CLI ≥ 0.122 · git · bash · Python 3.8+ · macOS、Linux，或 Windows 透過 WSL / Git Bash

### Claude Code

**1. 複製這段，貼給 Claude Code**
```
1. claude plugin marketplace add jaylooloomi/just-build-it
2. claude plugin install just-build-it@jaylooloomi-build --scope user
3. claude plugin list，確認 just-build-it@jaylooloomi-build 是 enabled
4. 在 ~/.claude/settings.json 的 "env" 加入 "CLAUDE_CODE_STOP_HOOK_BLOCK_CAP": "0"（保留既有內容）
5. 回報完成
```

**2. 開新 session，跳過權限確認**
```bash
claude --dangerously-skip-permissions
```
桌面版：Settings → Claude Code → 開啟「Allow bypass permissions mode」→ 開新 session 選 **Bypass permissions**。

**3. 先量，再放**
```
/just-build-it:build 只量                 # 看 SCOPE.md：模式、耦合度、FROZEN 清單
/just-build-it:build 8 --scope src/reports
```

8 小時後回來看 `CATALOG.md`。

### OpenAI Codex

**1. 複製這段，貼給 Codex**
```
1. codex plugin marketplace add jaylooloomi/just-build-it
2. codex plugin add just-build-it@jaylooloomi-build
3. 回報完成
```

**2. 開新 session，信任 hook**
```bash
codex --yolo
```
進去後輸入 `/hooks`，信任 just-build-it 的 hook（一次就好）。**沒做這步什麼都不會跑**。

**3. 輸入**
```
$build 8 --scope src/reports
```

<details>
<summary><b>Codex 上有什麼不同</b></summary>

小模型證據檢查 hook 不會跑（Codex 跳過 prompt 型 hook），所以「commit 前要有三題檢查輸出」只能靠 agent 自律；`scope-finalizer` / `candidate-picker` / `catalog-reporter` 子代理改用 Codex 自己的 agent 或獨立步驟代替。Stop hook 三階段計時、核心凍結防線、耦合稽核都是 command hook，Codex 一樣跑。`--yolo` 也關掉 sandbox；想保留可用 `--full-auto`，但 push 時可能停下來等你核准。**Codex 支援照 i-want-to-sleep 的作法移植，尚未實戰驗證。**
</details>

### 其他

<details>
<summary><b>只想裝在單一 repo？</b></summary>

第 1 步的 `--scope user` 換成 `--scope local`。
</details>

<details>
<summary><b>不想用 agent，自己裝</b></summary>

```bash
curl -fsSL https://raw.githubusercontent.com/jaylooloomi/just-build-it/main/install.sh | bash
```
然後 `~/.claude/settings.json` → `"env": { "CLAUDE_CODE_STOP_HOOK_BLOCK_CAP": "0" }`，`claude --dangerously-skip-permissions`。
</details>

<details>
<summary><b>這些設定在做什麼</b></summary>

| 設定 | 作用 |
|---|---|
| `--dangerously-skip-permissions` | 沒人按確認。**不要**把 `bypassPermissions` 寫進 `settings.local.json`：白天沒有 `ACTIVE` 檔，防線是關的 |
| `CLAUDE_CODE_STOP_HOOK_BLOCK_CAP=0` | Claude Code 預設連續 8 次 stop-hook 續跑就強制結束；`0` 取消。plugin 自己有時限與回合上限 |
| `HOARD_HOT_RATIO`（預設 0.08） | 熱點檔比例超過就判高耦合 → module 模式 |
| `HOARD_MAX_CYCLES`（預設 2） | 模組循環依賴超過就判高耦合 |
| `HOARD_PACK_PCT`（預設 10）／`HOARD_PACK_MIN`（預設 15） | 最後 N%（至少 N 分鐘）強制打包 |
| `HOARD_AUDIT_EVERY`（預設 5） | 每 N 回合重跑耦合稽核 |
| `HOARD_MAX_TURNS`（預設 300） | 回合數兜底 |

push 憑證只需能推到 `hoard/*`，請在 server 端保護 `main`。
</details>

<details>
<summary><b>試用 / 更新 / 移除</b></summary>

```bash
# 試用不安裝
git clone https://github.com/jaylooloomi/just-build-it.git
claude plugin validate ./just-build-it
claude --plugin-dir ./just-build-it/plugins/just-build-it

# 更新
claude plugin marketplace update jaylooloomi-build
claude plugin update just-build-it@jaylooloomi-build

# 移除
claude plugin uninstall just-build-it@jaylooloomi-build
claude plugin marketplace remove jaylooloomi-build
```
</details>

## 使用

分支是從**你當下的 HEAD** 開出去的（記在 `.hoard-pipeline/BASE`），MR 也該對它開——不是 main。

```
/just-build-it:build                         # 8 小時（預設），範圍由它量
/just-build-it:build 2 --scope src/reports   # 2 小時，鎖在一個目錄（建議每次都給）
/just-build-it:build 8 重點 匯出與報表         # 只調研與 X 有關的痛點
/just-build-it:build 只量                     # 只跑執行前檢查，寫 SCOPE.md 就停
/just-build-it:stop                       # 提前收工：手上的功能過三題就留、不過就丟
/just-build-it:stop 立刻                   # 手上的功能直接丟，立刻打包
```

人不在電腦前：從另一個終端機 `touch .hoard-pipeline/STOP`。Codex 用 `$build` / `$stop`。

### 隔天

人願意做的動作只有三種：看一眼、試一下、按刪除。超過這個就是上班。

1. 開 `CATALOG.md`。每個功能一張卡，≤ 3 行：一句話做什麼、怎麼開、怎麼刪，加一個「可刪檢查」結果。
2. 想試的：`features/flags.json` 改 `true`，或開總開關面板（CATALOG 第一行寫了怎麼開）。
3. 不要的：`rm -r features/NN-slug` ＋刪 flag 一行。標 `REMOVABLE` 的，刪了測試不會壞——這是打包階段實際搬走跑過測試的結果，不是模型說的。
4. 先看**被防線擋下**和**耦合稽核**兩段：前者是它想做什麼被擋、後者是功能有沒有偷偷互相依賴。這兩段決定你要不要讓它再跑一次。
5. 留下的開 MR（對 BASE），合併後刪 `.hoard-pipeline/`。


## 為什麼

大部分人的 token 用不完。而 AI 擅長的是加法（想功能、寫功能），人擅長的是減法（用過之後知道不要什麼）。問題是沒有人想花時間做減法——減法也是工作。

`/build` 把分工切乾淨：AI 在時限內不停地囤功能，但每一個都必須可開關、可刪除、附一張卡；人隔天只用拇指滑。**它不判斷功能好不好**——那是你用過之後才知道的事。它只保證每個功能拿出來試、丟回去的成本趨近零。

跟「自主演進」類 prompt 的差別：沒有方向錨，只有**邊界錨**。方向錨靠模型自己判斷會漂；邊界錨（哪些檔案不准碰）是量出來的，hook 真的會擋。

### 模型越強，它越強——但防線不用跟著變

這個 plugin 把兩種東西分開放：**判斷**交給模型，**紀律**交給腳本。所以每次換上更強的模型，自動變好的是前者：

| 隨模型升級會變好 | 不會變、也不需要變 |
|---|---|
| 調研抓到的痛點更準、來源更可靠 | 三題檢查（核心沒動／flag 關掉全綠／刪掉不壞） |
| 掛載點設計更貼技術棧，Step 2 更少出錯 | FROZEN 清單與 write-guard |
| 每個功能的程式碼與測試品質 | 最後 10% 強制打包 |
| 對「模糊 TODO」和「同質功能」的判斷 | 分支隔離、禁改清單、禁裝套件 |

換句話說：你不用等它「夠聰明」才敢放——防線今天就擋得住；而它產出的東西會隨著每一代模型自己變好，plugin 不用改一行。

## 執行時依序做什麼

下表是 `/just-build-it:build 8 --scope src/reports` 從輸入到收工的完整順序。「誰」欄標出每一步是腳本量的、模型判斷的、還是 hook 強制的——這是本工具的核心設計：**紀律給腳本，判斷給模型**。

| # | 階段 | 做什麼 | 產出 | 誰 |
|---|---|---|---|---|
| 0 | 開工 | 記錄目前分支為 BASE；stash 未提交變更；開 `hoard/<日期>` 分支；寫 DEADLINE = 現在 + 8h；立 ACTIVE 旗標（從此 hook 開始接管） | `.hoard-pipeline/{BASE,DEADLINE,ACTIVE}` | 模型執行指令 |
| 1a | 理解專案 | 讀 README、docs、ADR、CHANGELOG、入口檔、最近 30 天 commit，寫一段「專案目的」 | `SCOPE.md` 第 0 節 | 模型 |
| 1b | 量專案 | `preflight.py`：技術棧、產品型態、測試指令、依賴圖、扇入扇出、循環依賴、TODO/skip 清單 | `preflight.json`、`FROZEN`、`SCOPE.draft.md` | 腳本 |
| 1c | 定模式 | 依數字決定 whole / module / plugin；module 模式挑 TODO 最多的模組並把它的對外介面加進 FROZEN；找出可跑的測試指令 | `SCOPE.md`、`TEST_CMD`、`TESTS-START.md` | 腳本給數字，模型定稿 |
| 1d | 複核邊界 | `scope-finalizer` 檢查 FROZEN 是否涵蓋對外介面、功能落點在範圍內、測試真的能跑 | VERDICT | 小模型 |
| 2 | 建掛載點 | flag 讀取函式、功能註冊機制、總開關面板。**整晚唯一一次碰核心**，只能加不能改；做完加進 FROZEN | `features/flags.json`、掛載點 commit | 模型 |
| 2b | 收尾 | 範圍內、FROZEN 外的 TODO／失敗測試／skip 測試先做完，一項一 commit，revert 後測試仍綠才算；最多 10 項 | CATALOG「收尾」段 | 模型，`core_check.sh` + 測試把關 |
| 3 | 調研 | 以「專案目的」找 3 家同類產品，抓它們的負評與 issue（不抓功能表），每個候選附來源 | `candidates.md`（8–20 個） | 模型 |
| 4 | 挑一個 | `candidate-picker` 去重、剔除需新套件的、同家族最多 3 個、分散掛載點——**不評價好壞** | `PICK: n` | 小模型 |
| 5 | 做一個 | 寫在 `features/<NN-slug>/`，註冊 flag 預設 false，附自己的測試和一張卡 | 功能目錄 + 卡片 | 模型 |
| 5′ | 三題檢查 | ① `core_check.sh` 核心沒動？② 完整測試 flag 關閉全綠？③ `removability_check.sh` 搬走再跑測試仍綠？任一失敗重試 3 次，仍失敗就 revert 不留半成品 | commit 或 revert | 腳本 |
| ↻ | 迴圈 | commit 後回到第 4 步。每次模型想停下，Stop hook 看 DEADLINE 把它推回去；每 5 回合跑 `coupling_audit.py` 查功能是否互相引用 | 一回合一個功能 | hook |
| 6 | 打包 | 剩餘時間 ≤ 10%（至少 15 分鐘）hook 強制切換：不開新功能；手上的 10 分鐘內過不了三題就丟；對每個功能重跑可刪檢查；確認 flag 全關、面板可用；整理 CATALOG | `CATALOG.md` 定稿 | hook 觸發，模型執行 |
| 7 | 收工 | 時間到：再跑一次完整測試、`core_check.sh`、測試稽核；push 分支；立 DONE 旗標；`catalog-reporter` 產生「報告老闆」 | `TESTS-END.md`、push、報告 | hook 觸發，腳本 + 小模型 |

全程有三道 PreToolUse 防線在跑（不是提醒，是真的擋）：push 只能到 `hoard/*`、禁破壞性 git 與裝套件、禁寫 FROZEN 與 CI／migration／設定／依賴檔。

## 運作方式

```
/build 8 --scope src/reports
   │
   ▼
Step 0  記錄 BASE；開 hoard/<date>；ACTIVE 旗標；DEADLINE = 現在 + 8h
Step 1  先理解專案：讀 README / docs / ADR / 最近 commit，寫一段「專案目的」進 SCOPE.md
        執行前檢查（腳本量，不是模型猜）
        preflight.py → 技術棧 / 產品型態 / 測試指令 / 耦合度 / TODO 與 skip 測試清單
        → 模式：whole（低耦合有測試）/ module（高耦合，鎖一個模組）/ plugin（ERP、交易引擎，只碰擴充點）
        → FROZEN：扇入最高的檔案 → write-guard 真的擋
Step 2  建最小掛載點 + features/flags.json + 總開關面板（整晚唯一一次碰核心，做完也進 FROZEN）
Step 2b 收尾車道：先把開發者留的 TODO / 失敗測試 / skip 測試做完（範圍內、FROZEN 外；一項一 commit，可 git revert）
Step 3  調研：抓同類產品的負評和 issue，不抓功能表；每個候選要有來源
Step 4  挑一個：candidate-picker 只去重、去同質（同家族最多 3 個）、分散掛載點——不打價值分
Step 5  實作：一功能一目錄一 flag 一測試一卡片
        三題檢查過了才 commit：core_check.sh（核心沒動？）→ 完整測試（flag 關閉全綠？）→ removability_check.sh（搬走再跑，刪掉不壞？）
        過不了 → revert，不留 WIP
   ▲                         │
   └── 回到 Step 4 ◄─────────┘   每 5 回合 hook 重跑耦合稽核
最後 10%  打包階段：不開新功能；重跑可刪檢查；整理 CATALOG.md
Step 6  push 分支、貼「報告老闆」
```

讓它無人看管也不變成一團泥的三個機制：

- **Stop hook 三階段** — `hoarding` → `packaging`（剩餘時間 ≤ 10%，至少 15 分鐘）→ `finishing`。打包時間是硬預留的，不靠 agent 自覺。
- **PreToolUse hooks** — 確定性 shell script：擋 `hoard/*` 以外的 push、破壞性 git、裝套件、改 CI／migration／設定／依賴，**加上 `.hoard-pipeline/FROZEN` 內的路徑禁寫**（核心凍結）。
- **三題機械檢查** — 全部是腳本，不是模型判斷：

  | 題目 | 誰 | 怎麼量 |
  |---|---|---|
  | 核心有沒有被動？ | `core_check.sh` | `git diff BASE --name-only` ∩ FROZEN 必須為空 |
  | flag 關掉全綠？ | `TEST_CMD` | 完整測試（flag 預設 false） |
  | 刪掉會不會壞？ | `removability_check.sh` | 把功能目錄搬走、flag 拿掉、跑測試、搬回來 |
  | 功能互相依賴？ | `coupling_audit.py`（hook 每 5 回合） | `features/<a>/` 不得 import `features/<b>/` |

  小模型只做兩件不需要判斷力的事：`candidate-picker` 去重分散、prompt 型 Stop hook 查 transcript 有沒有留下上面的輸出。

## 搭配使用

| 指令 | 怎麼搭 |
|---|---|
| `/i-want-to-sleep:sleep` | 「做對一件事」用 sleep；「不要閒著」用 go。兩個 plugin 狀態目錄不同（`.agent-pipeline` / `.hoard-pipeline`），可同時裝 |
| `/build 只量` | 任何 repo 第一次都先量，看 FROZEN 清單合不合理，不合理就手動改 `.hoard-pipeline/FROZEN` 再放 |
| `/cost` | 看燒了多少，對照 `CATALOG.md` 統計的功能數，算「每個可用功能的 token 成本」 |
| `/goal` | 白天「做到某個終態」用 `/goal`；要囤用 `/build` |

## 相容性

| 執行環境 | 狀態 |
|---|---|
| Claude Code（CLI、桌面版、Remote Control）≥ 2.1.139 | ✅ 支援（尚未實戰） |
| OpenAI Codex CLI ≥ 0.122 | ✅ 支援——需在 `/hooks` 信任；無證據檢查 hook；指令 `$build` / `$stop`（尚未實戰） |
| claude.ai 網頁 / 手機聊天 | ❌ 無法無人看管地跑 session |
| Cursor、Gemini CLI、Copilot CLI … | ❌ 尚未 |

同一個 plugin 資料夾同時有 Claude Code manifest（`.claude-plugin/`）和 Codex manifest（`.codex-plugin/`）；Codex 執行同一套 hook 腳本。

## 內容物

| 路徑 | 作用 |
|---|---|
| `plugins/just-build-it/skills/feature-hoarder/SKILL.md` | 流程：理解專案 → 量 → 掛載點 → 收尾 TODO → 調研 → 挑 → 實作（三題）→ 打包 → 報告 |
| `plugins/just-build-it/skills/build/SKILL.md` | 開始 — `/just-build-it:build`（Claude Code）、`$build`（Codex） |
| `plugins/just-build-it/skills/stop/SKILL.md` | 提前結束 — `/just-build-it:stop`、`$stop` |
| `plugins/just-build-it/hooks/hooks.json` | 註冊四個 hook（3 個 command、1 個 prompt） |
| `plugins/just-build-it/scripts/preflight.py` | 執行前檢查：必讀文件清單、技術棧、產品型態、測試指令、耦合度、TODO/skip 掃描 → 模式 + FROZEN + SCOPE 草稿 |
| `plugins/just-build-it/scripts/hoard-stop.sh` | Stop hook：三階段（囤 → 打包 → 收工），週期耦合稽核 |
| `plugins/just-build-it/scripts/core_check.sh` | 三題之一：核心未動 |
| `plugins/just-build-it/scripts/removability_check.sh` | 三題之一：搬走跑測試再搬回 |
| `plugins/just-build-it/scripts/coupling_audit.py` | 功能之間禁互引 |
| `plugins/just-build-it/scripts/guard-bash.sh` / `guard-write.sh` | PreToolUse 防線（含 FROZEN 禁寫） |
| `plugins/just-build-it/scripts/test_audit.py` | 標出被刪除、弱化或 skip 的測試 |
| `plugins/just-build-it/agents/scope-finalizer.md` | Haiku：檢查 SCOPE.md 的邊界機制（不看方向） |
| `plugins/just-build-it/agents/candidate-picker.md` | Haiku：去重、去同質、分散——不評分 |
| `plugins/just-build-it/agents/catalog-reporter.md` | Haiku：產生「報告老闆」 |
| `.claude-plugin/marketplace.json` / `.agents/plugins/marketplace.json` | Claude Code / Codex marketplace |
| `tests/test_hoard.py` | 11 個腳本層測試 |
| `docs/design.md` | 設計筆記：為什麼是定時囤貨機 |

## 常見問題

**它會把我的 repo 變成一團泥嗎？**
這是它唯一的敵人，所以四道檢查全部是腳本量的：核心沒動、flag 關掉全綠、搬走不壞、功能不互引。過不了就 revert，不會留半成品。但門檻數字是估的（見限制）。

**它會先做完我留的 TODO 嗎？**
會，而且優先於新功能。preflight 掃出 TODO/FIXME 和被 skip 的測試，範圍內且不在 FROZEN 的先做，一項一 commit，revert 後測試仍綠才算。落在 FROZEN 裡的不做，列進「需要你決定的事」附位置。

**它怎麼知道什麼功能值得做？**
不知道，也不猜。它抓同類產品的使用者抱怨當選題來源（這是迴圈裡唯一不是模型自己產生的訊號），候選只做去重和分散。值不值得是你隔天刪的時候決定。

**跟 i-want-to-sleep 差在哪？**
sleep 有錨（對話裡的需求）、有 scorer 判斷值不值得、目標是把事做對。go 沒有方向錨、不評分、目標是不要閒著。前者產出 result.md ＋ MR，後者產出 CATALOG ＋ 一堆可刪的 flag。

**時限到了手上的功能做一半怎麼辦？**
丟掉。最後 10% 是打包階段，打包時 10 分鐘內過不了三題的功能直接 revert 並從 CATALOG 移除。囤的是完整樂高，不是零件。

**它會 push 到 `main` 嗎？**
不會。只放行 push 到 `hoard/*`。但請在 server 端保護 `main`——防線是黑名單。

**它記得上一次嗎？**
不記得。Step 0 清掉 `.hoard-pipeline/`。

## 限制

- **耦合度門檻是估的**（`HOARD_HOT_RATIO` 0.08、`HOARD_MAX_CYCLES` 2），沒跑過幾個專案前不準。先全部用 `--scope` 當 module 模式跑，寧可範圍小。
- **掛載點（Step 2）是整晚唯一碰核心的一次**，形式由 agent 依技術棧決定（路由／指令／事件／遊戲物件）。這是最容易出錯的一步，第一次跑請親自看那個 commit。
- 它會囤很多同質的低垂果實。「同家族最多 3 個」只能緩解。
- 沒有方向，所以不適合要「做對一件事」的場合——那是 i-want-to-sleep 的工作。
- 防線是 pattern 黑名單；真正的安全網是分支隔離＋受保護的 `main`。

## 貢獻

歡迎 issue 與 PR。開 PR 前跑 `python3 -m pytest -q tests` 與 `claude plugin validate .`。最想要的回報：你的 repo 在 `只量` 下的判定對不對、跑完後你花了幾分鐘、留下幾個功能。

## 授權

[MIT](LICENSE) © 2026 Arthur Wang。可自由使用、修改、再散布，包含商業用途，條件是保留版權聲明與授權全文。本軟體依「現狀」提供，不附任何擔保——無人看管的 agent 在你 repo 裡做的事，責任在使用者。
