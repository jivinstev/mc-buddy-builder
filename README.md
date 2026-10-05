# Buddy Builder

**A Claude Code mode that lets a young child build their own Minecraft mods, with a grown-up beside
them and the tests doing the code review.**

The child says what they want, out loud. Claude answers in short sentences a grown-up reads back,
breaks giant ideas into small playable pieces, and handles all the engineering itself: branches,
builds, tests, merging, deploying. The grown-up is only pulled in for real decisions, such as
anything that costs money, can't be undone, or goes outside the project.

```text
Child:   I want a dragon that breathes fire and gives you treasure!
Claude:  WOW, a treasure dragon! 🐉🔥 First I'll make your dragon that flies and breathes
         fire. Do you want to play with that first? Or should I make it drop treasure too,
         before you try it?
```

## Why it works: the tests are the review

A child can't read code, so "it's done" has to mean it works in the game. Buddy Builder holds Claude
to three gates before anything reaches the child:

| Gate | What runs | What it catches |
|---|---|---|
| A | Unit tests | Logic bugs |
| B | A headless game server | Crashes and broken registration that still compile |
| C | A real Minecraft client, scripted | What the player sees and hears |

[docs/TESTING.md](docs/TESTING.md) has the method and the rules that make those gates trustworthy.

## What's in this repo

| Path | What it is |
|---|---|
| `.claude/output-styles/buddy-builder.md` | The mode itself |
| `.claude/settings.json` | Turns the mode on and loads the enforced guardrails |
| `docs/SETUP.md` | Installing it in your mod project, switching it on and off |
| `docs/GUARDRAILS.md` | Which safety rules are enforced and which are behavioural |
| `docs/TESTING.md` | The three gates and the four rules |
| `docs/WORKFLOW.md` | How several sessions share one project without losing work |
| `docs/VERSIONS.md` | How one source tree builds two Minecraft versions |
| `setup`, `tools/buddy/` | First-run setup, renaming the mod, the version pipeline |
| `src/` | The starter mod: the Bounce Block and its three gates |

## Quick start

```bash
git clone https://github.com/jivinstev/mc-buddy-builder.git my-mod
cd my-mod
./setup          # picks your Minecraft version and mods folder, names the mod, makes your copy
claude           # then let the child say hi
```

You get a working NeoForge mod for Minecraft 1.21.1 or 26.2 with one example, a Bounce Block, and all
three gates already passing. Details in [docs/SETUP.md](docs/SETUP.md). To add the mode to a mod
you already have, copy `.claude/` into it instead. To install or port existing mods as well, pair it with
[mc-mod-version-upgrade](https://github.com/jivinstev/mc-mod-version-upgrade).

## Status

Early. The mode, guardrails, testing method and starter mod are here. CI builds the starter on both
Minecraft versions and runs all three gates on every push.

## Contributing

`tools/check-private-terms.py` runs on every push and pull request. It keeps personal names and
family details out of the repo, including commit messages. Install the local hooks with:

```bash
git config core.hooksPath .githooks
```

## Licence

MIT. See [LICENSE](LICENSE).
