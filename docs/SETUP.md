# Setting up Buddy Builder

## Use it in your own mod project

Copy two things into the root of your mod project:

```text
.claude/output-styles/buddy-builder.md
.claude/settings.json            # merge with yours if you already have one
```

Commit them. Anyone who opens the project in Claude Code starts in Buddy Builder mode, with the
guardrails loaded. A project setting only applies inside that project, so it never leaks into your
other work.

Then create a `.env.local` (not committed) with the folder your Minecraft instance loads mods from:

```text
MINECRAFT_MODS_DIR=/path/to/your/instance/mods
```

## Turning it on and off

- **It's on by default** in a project that has the settings file above.
- **Switch in a running session:** `/output-style` → **Buddy Builder** (or **Default**), then
  `/clear`. A style only takes effect at session start or after `/clear`, and `/clear` wipes the
  current chat.
- **Recommended:** keep two sessions open, one in Buddy Builder for the child and one in Default for
  grown-up work. They don't interfere with each other.

## Getting and porting existing mods

Buddy Builder can install mods from Modrinth or CurseForge and port mods stuck on old Minecraft
versions, using the skills in
[mc-mod-version-upgrade](https://github.com/jivinstev/mc-mod-version-upgrade). Clone it next to your
project and start Claude Code with both:

```bash
claude --add-dir ../mc-mod-version-upgrade
```

Added directories load their skills. Without it, Buddy Builder still builds features in your own mod;
it just can't fetch or port other mods.

## Things to know

- **The greeting appears on the first reply.** Claude Code has no banner before you type, so the
  welcome shows once the child says anything, even "hi".
- **Subagents don't inherit the style.** Only the main session's replies are written for the child.
  The main session summarises anything a subagent produces before the child hears it.
- **Don't bypass permission prompts in this mode.** The guardrails that ask the grown-up only work if
  a grown-up is there to answer. See `GUARDRAILS.md`.
- **Check the rules loaded** with `/permissions`.
