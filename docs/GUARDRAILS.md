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
| No force-push, hard reset or force branch delete | **Enforced** (`deny`) | `.claude/settings.json` |
| No `sudo` | **Enforced** (`deny`) | `.claude/settings.json` |
| Web browsing and downloads ask first | **Enforced** (`ask`): WebFetch, WebSearch, `curl`, `wget` prompt the grown-up | `.claude/settings.json` |
| Mods go only into `MINECRAFT_MODS_DIR` | Behavioural, plus the deploy task only writes there | output style; your build's deploy task |
| Grown-up asked before anything costly or irreversible | Behavioural | output style |
| Replies at an early-reader level | Behavioural | output style |
| Tests green before the child plays | Behavioural; the gates themselves are code | output style, `docs/TESTING.md` |

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
