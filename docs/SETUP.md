# Setting up Buddy Builder

## Start a new mod (recommended)

```bash
git clone https://github.com/jivinstev/mc-buddy-builder.git my-mod
cd my-mod
./setup
```

`./setup` asks four questions, each with a recommendation you can accept with Enter:

1. **Which Minecraft version.** If it finds a Minecraft install that already runs NeoForge on a
   supported version (1.21.1 or 26.2), it recommends that one and its mods folder. Otherwise it
   recommends 26.2, the newest.
2. **Where the mods folder is**, so `./gradlew deployToMods` can install your mod.
3. **Your mod's name.** Optional: you can let your child pick it later with `/name-my-mod`.
4. **Where your copy lives:**
   - **private** (recommended): a new private repo on your GitHub account. Updates from Buddy
     Builder still arrive through a remote called `upstream`.
   - **fork**: a public fork. GitHub forks of public repos are always public, so everything your
     child builds is visible to anyone.
   - **local**: no GitHub repo for now.

It writes `.env.local` (never committed) and turns on the git hooks. It's safe to run again: it keeps
your earlier answers and anything you edited by hand. `./setup --check` shows what it would change.

Your family builds and tests one Minecraft version. Buddy Builder's own CI builds both.

To bring in later improvements to Buddy Builder, ask Claude to run `/update-buddy-builder`.

## Add the mode to an existing mod project

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
