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

## Quick start

1. Copy `.claude/` into your mod project and commit it.
2. Add `MINECRAFT_MODS_DIR=/path/to/mods` to a `.env.local` that you don't commit.
3. Open the project in Claude Code. Let the child say hi.

Details in [docs/SETUP.md](docs/SETUP.md). To install or port existing mods as well, pair it with
[mc-mod-version-upgrade](https://github.com/jivinstev/mc-mod-version-upgrade).

## Status

Early. The mode, guardrails and testing method are here. A starter NeoForge mod with all three gates
already wired up is next.

## Contributing

`tools/check-private-terms.py` runs on every push and pull request. It keeps personal names and
family details out of the repo, including commit messages. Install the local hooks with:

```bash
git config core.hooksPath .githooks
```

## Licence

MIT. See [LICENSE](LICENSE).
