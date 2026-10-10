# Guardrails: what is enforced and what is behavioural

Buddy Builder has two kinds of safety rule. It matters which is which, because only one kind holds
when the model makes a mistake.

- **Enforced**: Claude Code refuses the action, or stops and asks the grown-up, because of a rule in
  `.claude/settings.json`. The model cannot talk its way past it.
- **Behavioural**: the output style tells the model to follow the rule. It usually will, but nothing
  stops it if it doesn't.

| Rule | How it holds | Where |
|---|---|---|
| No writes outside this project | **Enforced** by Claude Code's default: edits outside the working directory and any `additionalDirectories` need approval | Claude Code default |
| No reading SSH, cloud or shell credentials | **Enforced** (`deny`) | `.claude/settings.json` |
| No editing shell startup files | **Enforced** (`deny`) | `.claude/settings.json` |
| No `git stash` (shared between worktrees) | **Enforced** (`deny`) | `.claude/settings.json` |
| No forced `git worktree remove` (it throws away unsaved work) | **Enforced** (`deny`) | `.claude/settings.json` |
| No force-push, hard reset or force branch delete | **Enforced** (`deny`) | `.claude/settings.json` |
| No `sudo` | **Enforced** (`deny`) | `.claude/settings.json` |
| Web browsing asks first | **Enforced** (`ask`): WebFetch and WebSearch prompt the grown-up. Making a mod never needs them | `.claude/settings.json` |
| Making a mod never stops for approval | **Enforced** (`allow`): the build, the tests, setup, the repo's own scripts, everyday git and edits inside the project. Exact scripts, never folder wildcards | `.claude/settings.json`, checked by `tools/buddy/test_permissions.py` |
| The mod is named before anything is built | **Enforced** (`PreToolUse` hook): while it is still "Buddy Mod", edits under `src/` and `art/` are refused with a note to ask the child and run `/name-my-mod`. `KEEP_STARTER_NAME=yes` in `.env.local` keeps the starter name on purpose; `BUDDY_MAINTAINER=1` in the environment is for work on Buddy Builder itself | `.claude/hooks/name_guard.py`, checked by `tools/buddy/test_name_guard.py` |
| In the cloud, finished work lands on `main` | Behavioural: once all three gates pass, the session opens a pull request and merges it | output style |
| Mods go only into `MINECRAFT_MODS_DIR` | Behavioural, plus the deploy task only writes there | output style; your build's deploy task |
| Grown-up asked before anything costly or irreversible | Behavioural | output style |
| Replies at an early-reader level | Behavioural | output style |
| Tests green before the child plays | Behavioural; the gates themselves are code | output style, `docs/TESTING.md` |

## Why there are no prompts while making a mod

Every prompt a child meets mid-build is a grown-up being called over for nothing, and a habit of
clicking Allow without reading. So everything the mod-making workflow runs is allowed outright, and
only the rules worth a grown-up's attention still stop: web browsing (ask) and anything destructive
(deny). `curl` and `wget` used to ask too; they no longer do, because in the cloud the environment's
domain list already limits them, and at home Gradle and Python download freely anyway, so the rule
added prompts without adding protection.

Two things to know:

- **Trust the folder once.** Claude Code ignores a project's `allow` rules until you accept its trust
  dialog, which appears the first time you run `claude` in the folder. Until then everything prompts.
- **Prove it:** `python3 tools/buddy/test_permissions.py` checks the rules (CI runs it), and
  `--live` drives a real headless Claude Code in its strictest mode through the workflow and fails on
  any prompt.

## Tightening further

- **Mods folder.** Make your build's deploy task refuse any destination other than
  `MINECRAFT_MODS_DIR`, and copy atomically (temp file, then move) so a running game never reads a
  half-written jar.
- **Permission mode.** Don't run this mode with permission prompts bypassed. The `ask` rules only
  work if someone is there to answer them.
- **Per machine.** Anything specific to your computer (extra denied paths, your mods folder) belongs
  in `.claude/settings.local.json`, which is not committed.

## Checking it

Run `/permissions` in a session to see the rules Claude Code actually loaded. If the list is empty,
the project settings were not picked up.
