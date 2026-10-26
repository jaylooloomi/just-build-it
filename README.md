<h1 align="center">just-build-it 🔨</h1>

<p align="center">
  <b>Nobody wants to work. So let the agent hoard.</b><br>
  Type <code>/build 8 --scope src/reports</code>. Walk away. Come back to a crate of features, each one toggleable and deletable in one command. Swipe, keep what you like, delete the rest.
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="license MIT"></a>
  <img src="https://img.shields.io/badge/version-0.1.0-informational" alt="version 0.1.0">
  <img src="https://img.shields.io/badge/platform-macOS%20%7C%20Linux%20%7C%20WSL-lightgrey" alt="platform macOS | Linux | WSL">
  <img src="https://img.shields.io/badge/Python-3.8%2B-3776AB" alt="Python 3.8+">
  <img src="https://img.shields.io/badge/Claude%20Code-plugin-D97757" alt="Claude Code plugin">
  <img src="https://img.shields.io/badge/Codex-plugin-black" alt="Codex plugin">
  <a href="tests"><img src="https://img.shields.io/badge/tests-11%20passing-brightgreen" alt="tests 11 passing"></a>
  <a href="README.zh-TW.md"><img src="https://img.shields.io/badge/lang-繁體中文-green" alt="繁體中文"></a>
</p>

## Use cases

| Situation | Command | Why it fits |
|---|---|---|
| 🛋️ **Weekend, long holiday** | `/build 24 --scope src/game` | No brief needed. It mines what users of similar products complain about and turns each complaint into a toggleable feature |
| 💳 **Subscription quota about to reset** | `/build 3 --scope <any module>` | Burn the quota into feature inventory before it vanishes |
| 🧪 **See how it judges my repo first** | `/build measure only` | Runs preflight only, writes SCOPE.md and stops — read the coupling numbers and the mode it picked before you let it loose |
| 🔍 **What are competitor users complaining about?** | `/build 2 focus on export and reporting` | The research step scrapes negative reviews and issues, not feature lists |
| 🏚️ **Legacy, tightly coupled, scared to touch** | `/build 8` (it will pick module or plugin mode itself) | The frozen-core list is measured by a script and enforced by a hook; features mount onto the core, never modify it |
| 🌙 **Overnight handover, finish what the chat started** | ❌ use [i-want-to-sleep](https://github.com/jaylooloomi/i-want-to-sleep) | That one does *the right thing*; this one *never idles*. They install side by side |

On Codex use `$build` instead: `$build 3 --scope src/api`.

## Install

**Requires:** Claude Code ≥ 2.1.139 or Codex CLI ≥ 0.122 · git · bash · Python 3.8+ · macOS, Linux, or Windows via WSL / Git Bash

### Claude Code

**1. Paste this to Claude Code**
```
1. claude plugin marketplace add jaylooloomi/just-build-it
2. claude plugin install just-build-it@jaylooloomi-build --scope user
3. claude plugin list, confirm just-build-it@jaylooloomi-build is enabled
4. In ~/.claude/settings.json add "CLAUDE_CODE_STOP_HOOK_BLOCK_CAP": "0" under "env" (keep existing entries)
5. Report done
```

**2. Open a new session with permissions bypassed**
```bash
claude --dangerously-skip-permissions
```
Desktop app: Settings → Claude Code → enable "Allow bypass permissions mode" → new session → pick **Bypass permissions**.

**3. Measure first, then let go**
```
/just-build-it:build measure only          # read SCOPE.md: mode, coupling, FROZEN list
/just-build-it:build 8 --scope src/reports
```

Come back in 8 hours and open `CATALOG.md`.

### OpenAI Codex

**1. Paste this to Codex**
```
1. codex plugin marketplace add jaylooloomi/just-build-it
2. codex plugin add just-build-it@jaylooloomi-build
3. Report done
```

**2. New session, trust the hooks**
```bash
codex --yolo
```
Inside, type `/hooks` and trust just-build-it's hooks (once). **Nothing runs until you do.**

**3. Type**
```
$build 8 --scope src/reports
```

<details>
<summary><b>What's different on Codex</b></summary>

The small-model evidence-check hook does not run (Codex skips prompt hooks), so "show the three-gate output before every commit" relies on the agent's discipline. The `scope-finalizer` / `candidate-picker` / `catalog-reporter` subagents are replaced by Codex's own agents or standalone steps. The three-phase Stop hook timer, frozen-core guard and coupling audit are command hooks and run identically. `--yolo` also disables the sandbox; `--full-auto` keeps it but may pause on network (push). **Codex support is ported from i-want-to-sleep and not yet field-tested.**
</details>

### Other

<details>
<summary><b>Only one repo?</b></summary>

Replace `--scope user` with `--scope local` in step 1.
</details>

<details>
<summary><b>Install by hand</b></summary>

```bash
curl -fsSL https://raw.githubusercontent.com/jaylooloomi/just-build-it/main/install.sh | bash
```
Then `~/.claude/settings.json` → `"env": { "CLAUDE_CODE_STOP_HOOK_BLOCK_CAP": "0" }` and `claude --dangerously-skip-permissions`.
</details>

<details>
<summary><b>What the settings do</b></summary>

| Setting | Effect |
|---|---|
| `--dangerously-skip-permissions` | No one is there to approve. **Don't** put `bypassPermissions` in `settings.local.json`: during the day there is no `ACTIVE` file and the guards are off |
| `CLAUDE_CODE_STOP_HOOK_BLOCK_CAP=0` | Claude Code force-ends a turn after 8 consecutive stop-hook continuations; `0` removes that cap. The plugin has its own deadline and turn cap |
| `HOARD_HOT_RATIO` (default 0.08) | Share of hot files (fan-in ≥ 5) above which the repo counts as tightly coupled → module mode |
| `HOARD_MAX_CYCLES` (default 2) | Module-level dependency cycles above which it counts as tightly coupled |
| `HOARD_PACK_PCT` (default 10) / `HOARD_PACK_MIN` (default 15) | Last N % of time (at least N minutes) is forced packaging |
| `HOARD_AUDIT_EVERY` (default 5) | Re-run the coupling audit every N turns |
| `HOARD_MAX_TURNS` (default 300) | Turn-count backstop |

Push credentials only need to reach `hoard/*`; protect `main` server-side.
</details>

<details>
<summary><b>Try / update / remove</b></summary>

```bash
# try without installing
git clone https://github.com/jaylooloomi/just-build-it.git
claude plugin validate ./just-build-it
claude --plugin-dir ./just-build-it/plugins/just-build-it

# update
claude plugin marketplace update jaylooloomi-build
claude plugin update just-build-it@jaylooloomi-build

# remove
claude plugin uninstall just-build-it@jaylooloomi-build
claude plugin marketplace remove jaylooloomi-build
```
</details>

## Usage

The branch is cut from **your current HEAD** (recorded in `.hoard-pipeline/BASE`); open the MR against it, not `main`.

```
/just-build-it:build                              # 8 hours (default), scope measured by preflight
/just-build-it:build 2 --scope src/reports        # 2 hours, locked to one directory (recommended every time)
/just-build-it:build 8 focus on export            # research only pain points related to X
/just-build-it:build measure only                 # preflight only, write SCOPE.md and stop
/just-build-it:stop                            # early finish: current feature kept if it passes the three gates, dropped otherwise
/just-build-it:stop now                        # drop the current feature, package immediately
```

Away from the keyboard: `touch .hoard-pipeline/STOP` from another terminal. On Codex use `$build` / `$stop`.

### The next morning

A human will do exactly three things: glance, try, delete. Anything more is work.

1. Open `CATALOG.md`. One card per feature, ≤ 3 lines: what it does, how to enable, how to delete, plus a deletability result.
2. Want to try one: flip it to `true` in `features/flags.json`, or open the feature panel (the first line of the CATALOG says how).
3. Don't want it: `rm -r features/NN-slug` and delete its flag line. Cards marked `REMOVABLE` were physically moved out and the test suite re-run during packaging — that's a script result, not the model's opinion.
4. Read **Blocked by guards** and **Coupling audit** first: what it tried to do and got stopped, and whether features started depending on each other. These two sections decide whether you let it run again.
5. Open an MR for the keepers (against BASE); delete `.hoard-pipeline/` after merge.


## Why

Most people never use up their tokens. AI is good at addition (inventing and writing features); humans are good at subtraction (knowing what they don't want once they've used it). The catch: nobody wants to spend time on subtraction either — subtraction is work.

`/build` splits the job cleanly. The agent hoards features non-stop until the deadline, but every one must be toggleable, deletable, and carry a card. The human swipes with a thumb the next morning. **It does not judge whether a feature is good** — you only know that after using it. It guarantees that trying one and throwing it back costs almost nothing.

Versus "self-evolving" prompts: there is no direction anchor, only a **boundary anchor**. A direction anchor depends on the model's judgment and drifts; a boundary anchor (which files are off-limits) is measured and enforced by a hook.

### Smarter model, better hoard — same guards

The plugin keeps two things apart: **judgment** lives in the model, **discipline** lives in scripts. So every time you swap in a stronger model, the first column improves on its own:

| Gets better with each model | Stays the same, by design |
|---|---|
| Pain points found in research are sharper, sources more reliable | The three gates (core untouched / green with flags off / still green when deleted) |
| Mount-point design fits the stack better, Step 2 fails less | The FROZEN list and the write guard |
| Code and test quality of every feature | Forced packaging in the last 10 % |
| Judgment on vague TODOs and same-flavoured features | Branch isolation, protected files, no package installs |

In other words: you don't wait for it to be "smart enough" before letting it loose — the guards hold today. What it produces improves with every model generation without changing a line of the plugin.

## How it works

```
/build 8 --scope src/reports
   │
   ▼
Step 0  record BASE; branch hoard/<date>; ACTIVE flag; DEADLINE = now + 8h
Step 1  understand the project first: read README / docs / ADRs / recent commits, write a one-paragraph "purpose" into SCOPE.md
        preflight (measured by a script, not guessed by the model)
        preflight.py → stack / product type / test command / coupling / TODO & skipped-test list
        → mode: whole (loose, has tests) / module (tight, lock one module) / plugin (ERP, trading engine: extension points only)
        → FROZEN: highest fan-in files → write-guard actually blocks them
Step 2  minimal mount point + features/flags.json + feature panel (the only touch of the core all night; frozen afterwards)
Step 2b wrap-up lane: finish the TODOs / failing tests / skipped tests developers left (in scope, outside FROZEN; one commit each, git-revertable)
Step 3  research: competitors' negative reviews and issues, not feature lists; every candidate cites a source
Step 4  pick one: candidate-picker dedupes, caps families at 3, spreads mount points — no value score
Step 5  build: one feature = one directory + one flag + its own tests + one card
        commit only after three gates: core_check.sh (core untouched?) → full suite (flag off, green?) → removability_check.sh (move it out, still green?)
        fail → revert, no WIP left behind
   ▲                         │
   └── back to Step 4 ◄──────┘   hook re-runs the coupling audit every 5 turns
last 10%  packaging: no new features; re-run deletability; tidy CATALOG.md
Step 6  push the branch, post the wrap-up
```

Three mechanisms keep it from turning your repo into mud while unattended:

- **Three-phase Stop hook** — `hoarding` → `packaging` (≤ 10 % of time left, at least 15 min) → `finishing`. Packaging time is reserved by the hook, not by the agent's good will.
- **PreToolUse hooks** — deterministic shell scripts: block pushes outside `hoard/*`, destructive git, package installs, edits to CI / migrations / config / dependency files, **plus any path in `.hoard-pipeline/FROZEN`** (frozen core).
- **Three mechanical gates** — all scripts, no model judgment:

  | Question | Who | How it is measured |
  |---|---|---|
  | Core untouched? | `core_check.sh` | `git diff BASE --name-only` ∩ FROZEN must be empty |
  | Green with the flag off? | `TEST_CMD` | full suite (flags default to false) |
  | Still green if deleted? | `removability_check.sh` | move the feature directory out, drop its flag, run the suite, move it back |
  | Features depending on each other? | `coupling_audit.py` (hook, every 5 turns) | `features/<a>/` must not import `features/<b>/` |

  The small model only does two things that need no judgment: `candidate-picker` dedupes and spreads; the prompt-type Stop hook checks that the transcript actually shows the outputs above.

## Works with

| Command | How |
|---|---|
| `/i-want-to-sleep:sleep` | *Do the right thing* → sleep. *Never idle* → go. Separate state dirs (`.agent-pipeline` / `.hoard-pipeline`), install both |
| `/build measure only` | Run once on any new repo; if the FROZEN list looks wrong, edit `.hoard-pipeline/FROZEN` by hand before letting it run |
| `/cost` | Compare spend against the feature count in `CATALOG.md`: tokens per usable feature |
| `/goal` | Daytime "reach a verifiable end state" → `/goal`; hoarding → `/build` |

## Compatibility

| Runtime | Status |
|---|---|
| Claude Code (CLI, desktop, Remote Control) ≥ 2.1.139 | ✅ supported (not yet field-tested) |
| OpenAI Codex CLI ≥ 0.122 | ✅ supported — trust in `/hooks`; no evidence-check hook; commands `$build` / `$stop` (not yet field-tested) |
| claude.ai web / mobile chat | ❌ can't run an unattended session |
| Cursor, Gemini CLI, Copilot CLI … | ❌ not yet |

The same plugin folder carries both the Claude Code manifest (`.claude-plugin/`) and the Codex manifest (`.codex-plugin/`); Codex runs the same hook scripts.

## What's inside

| Path | Role |
|---|---|
| `plugins/just-build-it/skills/feature-hoarder/SKILL.md` | The loop: understand → measure → mount point → wrap up TODOs → research → pick → build (three gates) → package → report |
| `plugins/just-build-it/skills/build/SKILL.md` | Start — `/just-build-it:build` (Claude Code), `$build` (Codex) |
| `plugins/just-build-it/skills/stop/SKILL.md` | Early finish — `/just-build-it:stop`, `$stop` |
| `plugins/just-build-it/hooks/hooks.json` | Registers four hooks (3 command, 1 prompt) |
| `plugins/just-build-it/scripts/preflight.py` | Preflight: must-read docs, stack, product type, test command, coupling, TODO/skip scan → mode + FROZEN + SCOPE draft |
| `plugins/just-build-it/scripts/hoard-stop.sh` | Stop hook: three phases (hoard → package → finish), periodic coupling audit |
| `plugins/just-build-it/scripts/core_check.sh` | Gate: core untouched |
| `plugins/just-build-it/scripts/removability_check.sh` | Gate: move out, test, move back |
| `plugins/just-build-it/scripts/coupling_audit.py` | No imports between features |
| `plugins/just-build-it/scripts/guard-bash.sh` / `guard-write.sh` | PreToolUse guards (incl. FROZEN) |
| `plugins/just-build-it/scripts/test_audit.py` | Flags deleted, weakened or skipped tests |
| `plugins/just-build-it/agents/scope-finalizer.md` | Haiku: checks SCOPE.md boundary mechanics (never direction) |
| `plugins/just-build-it/agents/candidate-picker.md` | Haiku: dedupe, family cap, spread — no scoring |
| `plugins/just-build-it/agents/catalog-reporter.md` | Haiku: writes the wrap-up message |
| `.claude-plugin/marketplace.json` / `.agents/plugins/marketplace.json` | Claude Code / Codex marketplaces |
| `tests/test_hoard.py` | 11 script-level tests |
| `docs/design.md` | Design notes: why a timed hoarder |

## FAQ

**Will it turn my repo into mud?**
That is its only enemy, so all four checks are scripts: core untouched, green with flags off, still green when moved out, no cross-feature imports. Fail → revert, never a half-built feature. The thresholds are estimates though (see Limitations).

**Will it finish the TODOs I left first?**
Yes, and before any new feature. Preflight scans TODO/FIXME lines and skipped tests; those in scope and outside FROZEN get done first, one commit each, counted only if the suite is still green after reverting that commit. TODOs inside FROZEN are not touched and are listed under "needs your decision" with their location.

**How does it know which features are worth building?**
It doesn't, and doesn't guess. It mines complaints from users of similar products as the source of candidates (the only signal in the loop the model didn't generate itself), then only dedupes and spreads. Worth is decided by you, with the delete key, the next morning.

**How is this different from i-want-to-sleep?**
sleep has an anchor (the requirement in the chat), a scorer that judges worth, and aims to get one thing right. go has no direction anchor, no scoring, and aims to never idle. One yields result.md + an MR; the other yields a CATALOG + a pile of deletable flags.

**Deadline hits mid-feature?**
It's dropped. The last 10 % is packaging; anything that can't pass the three gates within 10 minutes is reverted and removed from the CATALOG. It hoards finished bricks, not parts.

**Will it push to `main`?**
No. Only pushes to `hoard/*` pass the guard. Still protect `main` server-side — guards are blocklists.

**Does it remember last time?**
No. Step 0 wipes `.hoard-pipeline/`.

## Limitations

- **Coupling thresholds are guesses** (`HOARD_HOT_RATIO` 0.08, `HOARD_MAX_CYCLES` 2) until a few repos have been through. Start with `--scope` (module mode) every time; smaller is safer.
- **The mount point (Step 2) is the one touch of the core all night**, and its shape (route / command / event / game object) is chosen by the agent per stack. It is the most error-prone step — review that commit yourself on your first run.
- It will hoard plenty of same-flavoured low-hanging fruit. The "3 per family" cap mitigates, not cures.
- No direction, so wrong for "get one thing right" — that's i-want-to-sleep's job.
- Guards are pattern blocklists; the real safety net is branch isolation plus a protected `main`.

## Contributing

Issues and PRs welcome. Before a PR run `python3 -m pytest -q tests` and `claude plugin validate .`. Most wanted reports: whether `measure only` judged your repo correctly, and after a run, how many minutes you spent swiping and how many features you kept.

## License

[MIT](LICENSE) © 2026 Arthur Wang. Free to use, modify and redistribute, including commercially, as long as the copyright notice and license text stay. Provided as is, without warranty — what an unattended agent does in your repo is on you.
