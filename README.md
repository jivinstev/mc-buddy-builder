# Buddy Builder

**A Claude Code mode that lets a young child build their own Minecraft mods, with a grown-up beside
them and the tests doing the code review.**

```text
Child:   I want a dragon that breathes fire and gives you treasure!
Claude:  WOW, a treasure dragon! 🐉🔥 First I'll make your dragon that flies and breathes
         fire. Do you want to play with that first? Or should I make it drop treasure too?
```

You get a working NeoForge mod for Minecraft 1.21.1 or 26.2, with one example (a Bounce Block) and
three test gates already passing: unit tests, a headless game server, and a real game client. Claude
won't call a feature done until all three pass.

## Quick start

On a Mac with Minecraft: Java Edition (open the launcher once and sign in first):

```bash
git clone https://github.com/jivinstev/mc-buddy-builder.git my-mod
cd my-mod && ./setup
claude                   # then let your child say hi
```

`./setup` does the rest, and every question has a recommended answer you can accept with Enter:

- installs Java 21 and Claude Code for you if they're missing;
- installs NeoForge into your Minecraft launcher, as a **Buddy Builder** profile with its own mods
  folder, so your normal worlds stay untouched;
- names the mod (or your child can do it later);
- makes your own private copy on GitHub, still linked here so Buddy Builder updates keep arriving.

Then open the Minecraft launcher, pick the **Buddy Builder** profile, and play. Each time your child
finishes something, Claude puts the new version of the mod in that profile's mods folder.

**Clone this repo; don't use "Use this template".** A template copy shares no history with Buddy
Builder, so it can't take updates. `./setup` makes your private copy for you.

**Only on a Mac for now.** Windows support is planned
([#1](https://github.com/jivinstev/mc-buddy-builder/issues/1)). Cloud sessions (claude.ai/code) can
build and test but can't play, so they aren't supported yet either
([#2](https://github.com/jivinstev/mc-buddy-builder/issues/2)); [docs/CLOUD.md](docs/CLOUD.md) has the
unsupported steps for anyone who wants to try.

## More

| | |
|---|---|
| [docs/SETUP.md](docs/SETUP.md) | Setup in detail; adding the mode to a mod you already have |
| [docs/TESTING.md](docs/TESTING.md) | The three gates, and the rules that make them trustworthy |
| [docs/GUARDRAILS.md](docs/GUARDRAILS.md) | Which safety rules are enforced and which are behavioural |
| [docs/WORKFLOW.md](docs/WORKFLOW.md) | Several sessions sharing one project without losing work |
| [docs/VERSIONS.md](docs/VERSIONS.md) | One source tree, two Minecraft versions |

To install other people's mods or port ones stuck on an old version, pair it with
[mc-mod-version-upgrade](https://github.com/jivinstev/mc-mod-version-upgrade).

## Contributing

CI runs every gate on both Minecraft versions, plus a check that keeps personal names out of the repo
(commit messages included). Install the local hooks with `git config core.hooksPath .githooks`.

## Licence

MIT. See [LICENSE](LICENSE).
