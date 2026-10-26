<h1 align="center">just-build-it 🔨 做就對了</h1>

<p align="center">
  <b>人就是不想上班。</b><br>
  輸入 <code>/go 8 --scope src/報表</code>，去做別的事。回來：一箱可獨立開關、可一鍵刪除的功能，滑過去、留想要的、其他刪掉。
</p>

## 它跟 i-want-to-sleep 差在哪

| | [i-want-to-sleep](https://github.com/jaylooloomi/i-want-to-sleep) | just-build-it |
|---|---|---|
| 給它什麼 | 一段做到一半的對話 | 一個 repo（或一個子目錄）和幾小時 |
| 錨 | 對話裡的原始需求 | **沒有方向錨，只有邊界錨**：量出來的 FROZEN 清單 |
| 誰判斷值不值得 | scorer 子代理 | **沒有人**。價值判斷留給你隔天的拇指 |
| 守門 | 分數門檻 | **三題機械檢查**：核心沒動？flag 關掉全綠？刪掉不壞？ |
| 產出 | result.md ＋ 可開 MR 的分支 | **CATALOG.md**：每個功能一張卡（一句話／怎麼開／怎麼刪） |
| 結束 | 時間到 | 時間到，**最後 10% 強制打包**，不留半成品 |

設計原理一句話：加法靠想像，減法靠回饋。AI 擅長前者，人擅長後者；這個 plugin 只讓 AI 做前者，並把後者的成本壓到「滑卡片」。

## 它怎麼跑

```
/go 8 --scope src/reports
   │
   ├─ Step 1  執行前檢查（腳本量，不是模型猜）
   │     preflight.py → 技術棧 / 產品型態 / 測試指令 / 耦合度
   │     → 模式：whole（低耦合有測試）/ module（高耦合 → 鎖在一個模組）/ plugin（ERP、交易引擎 → 只碰擴充點）
   │     → FROZEN：扇入最高的檔案，PreToolUse hook 真的會擋寫入
   │
   ├─ Step 2  建最小掛載點 + features/flags.json + 總開關面板（整晚唯一一次碰核心）
   │
   ├─ Step 3–5  囤（Stop hook 把它推回來，直到時間到）
   │     調研：抓同類產品的「負評和 issue」，不抓功能表
   │     挑選：candidate-picker 只去重、去同質、分散掛載點——不評分
   │     實作：一功能一目錄一 flag 一測試一卡片
   │     三題檢查過了才 commit；過不了就 revert，不留 WIP
   │     每 5 回合 hook 重跑耦合稽核：功能互相依賴 → 立刻解開
   │
   ├─ 最後 10% 時間  打包階段：不開新功能，重跑可刪檢查，整理 CATALOG.md
   │
   └─ 時間到  push 到 hoard/<date>，貼「報告老闆」
```

## 安裝

**需求：** Claude Code ≥ 2.1.139 或 Codex CLI ≥ 0.122 · git · bash · Python 3.8+ · macOS / Linux / WSL

### Claude Code

```
1. claude plugin marketplace add jaylooloomi/just-build-it
2. claude plugin install just-build-it@jaylooloomi-build --scope user
3. 在 ~/.claude/settings.json 的 "env" 加入 "CLAUDE_CODE_STOP_HOOK_BLOCK_CAP": "0"
4. claude --dangerously-skip-permissions
5. /just-build-it:go 8 --scope <目錄>
```

或一行：`curl -fsSL https://raw.githubusercontent.com/jaylooloomi/just-build-it/main/install.sh | bash`

想先看它會怎麼判定你的 repo：`/just-build-it:go 只量`，它跑完 preflight 寫出 SCOPE.md 就停。

### OpenAI Codex

```
1. codex plugin marketplace add jaylooloomi/just-build-it
2. codex plugin add just-build-it@jaylooloomi-build
3. codex --yolo
4. 進去後輸入 /hooks，信任 just-build-it 的 hook（一次就好；沒做這步什麼都不會跑）
5. $go 8 --scope <目錄>
```

Codex 上的差異：小模型證據檢查 hook 不會跑（Codex 跳過 prompt 型 hook），所以「commit 前要有三題檢查輸出」只能靠 agent 自律；`scope-finalizer` / `candidate-picker` / `catalog-reporter` 改用 Codex 的 agent 或獨立步驟代替。Stop hook 三階段計時、核心凍結防線、耦合稽核都是 command hook，Codex 一樣會跑。**Codex 支援只照 i-want-to-sleep 的作法移植，尚未實戰驗證。**

## 參數

| 參數 | 意思 |
|---|---|
| `<數字>` | 時數，預設 8 |
| `--scope <目錄>` | 強制區域模組模式。**建議每次都給**：不給時它會挑痛點最多的模組，但可能挑錯 |
| `重點 X` | 只調研與 X 有關的痛點 |
| `只量` | 只跑執行前檢查，寫 SCOPE.md 就收工 |
| `/just-build-it:stop [立刻]` | 提前收工；`立刻` = 手上的功能直接丟掉 |
| Codex | `$go` / `$stop`，參數相同 |

## 隔天你做什麼

1. 開 `CATALOG.md`，每張卡 3 行。
2. 想試的：`features/flags.json` 改 `true`，或開總開關面板。
3. 不要的：`rm -r features/NN-slug` ＋刪 flag 一行。卡片上有「可刪檢查」結果，REMOVABLE 的刪了測試不會壞。
4. 留下的開 MR（對 BASE 分支，不是 main）。

## 適用範圍（它啟動時會自己量）

| 專案 | 判定 | 行為 |
|---|---|---|
| 小工具、CLI、遊戲、函式庫、低耦合 web | whole | 整個 repo 都可以掛功能 |
| 大型 web / 後台、高耦合 | module | 鎖在一個模組，模組對外介面進 FROZEN |
| ERP、交易引擎、帳務、無測試的舊系統 | plugin | 不碰既有程式碼，只寫擴充點 |

門檻可用環境變數調：`HOARD_HOT_RATIO`（預設 0.08）、`HOARD_MAX_CYCLES`（2）、`HOARD_PACK_PCT`（10）、`HOARD_PACK_MIN`（15 分鐘）、`HOARD_AUDIT_EVERY`（5 回合）、`HOARD_MAX_TURNS`（300）。

## 防線（hook 真的會擋，不是提醒）

- Git：只在 `hoard/*`；禁 merge / rebase / reset --hard / force push / 切主分支
- 核心凍結：`.hoard-pipeline/FROZEN` 內的路徑禁寫
- 禁改清單：CI、migration、設定檔、依賴清單
- 禁新增第三方套件
- 功能之間禁互引（每 5 回合稽核）
- 證據協議：每回合要有工具呼叫、`git status --short`、commit 前要有三題檢查輸出

## 已知限制

- 耦合度門檻是估的，沒跑過幾個專案前不準；先全部當 module 模式用，寧可範圍小。
- 掛載點的形式（路由／指令／事件／遊戲物件）由 agent 依技術棧決定，前後端混合 repo 可能判斷模糊——用 `--scope` 指定。
- 它會囤很多同質的低垂果實。candidate-picker 的「同家族最多 3 個」只能緩解，不能根治。
- 沒有方向，所以不適合要「做對一件事」的場合——那是 i-want-to-sleep 的工作。

## 開發

```bash
python3 -m pytest -q tests
```

MIT © 2026 Arthur Wang
