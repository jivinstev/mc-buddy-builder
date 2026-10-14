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

First install Minecraft: Java Edition from minecraft.net, open the launcher once and sign in, then
quit it.

### On a Mac

```bash
git clone https://github.com/jivinstev/mc-buddy-builder.git my-mod
cd my-mod && ./setup
claude                   # then let your child say hi
```

### On Windows

1. Open **PowerShell** from the Start menu with a plain click. Don't use "Run as administrator": the
   title bar must **not** start with "Administrator:". (The installer checks, and stops if it is.)
2. Go to the folder where you keep code, for example `cd ~\dev`. The project goes in a folder inside
   it, and the installer asks before using it.
3. Paste this line:

```powershell
irm https://raw.githubusercontent.com/jivinstev/mc-buddy-builder/main/install.ps1 | iex
```

It installs Git and Python with winget if they're missing, downloads Buddy Builder, runs setup, and
starts Claude Code. Next time, open PowerShell, `cd` into the project and type `claude`.

<details>
<summary>Doing the same by hand</summary>

```powershell
winget install -e --source winget --id Git.Git
winget install -e --source winget --id Python.Python.3.12
# open a new PowerShell window, then:
git clone https://github.com/jivinstev/mc-buddy-builder.git my-mod
cd my-mod
.\setup.cmd
claude
```

`--source winget` matters: without it, a broken Microsoft Store source (common on VMs and work
networks) makes winget install nothing. In Git Bash, `./setup` works too, but answer its questions
from PowerShell: Git Bash's window can't pass your answers to Windows Python.
</details>

### What setup does

Setup does the rest, and every question has a recommended answer you can accept with Enter:

- installs Java 21 and Claude Code for you if they're missing (no administrator password needed);
- installs NeoForge into your Minecraft launcher, as a **Buddy Builder** profile with its own mods
  folder, so your normal worlds stay untouched;
- names the mod (or your child can do it later);
- makes your own private copy on GitHub, still linked here so Buddy Builder updates keep arriving.

To get Buddy Builder updates later, run setup again (`./setup`, or `.\setup.cmd` on Windows).

Then open the Minecraft launcher, pick the **Buddy Builder** profile, and play. Each time your child
finishes something, Claude puts the new version of the mod in that profile's mods folder.

**Clone this repo; don't use "Use this template".** A template copy shares no history with Buddy
Builder, so it can't take updates. `./setup` makes your private copy for you.

**Mac and Windows.** Windows is native, through Git Bash, which Claude Code uses there; WSL isn't
needed. Claude Code has no sandbox on native Windows, and Buddy Builder doesn't rely on one: its
guardrails are permission rules, which work the same on both. Cloud sessions (claude.ai/code) can
build and test but can't play, so they aren't supported yet
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

CI runs every gate on both Minecraft versions, on Linux and on Windows, plus a check that keeps
personal names out of the repo (commit messages included). On Windows it also runs the one-line
install. Install the local hooks with `git config core.hooksPath .githooks`.

## Licence

MIT. See [LICENSE](LICENSE).
