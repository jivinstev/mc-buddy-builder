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

## Quick start: on your computer

```bash
git clone https://github.com/jivinstev/mc-buddy-builder.git my-mod
cd my-mod && ./setup     # finds your Minecraft, names the mod, makes your private copy
claude                   # then let your child say hi
```

Needs git, Python 3, Java 21 and [Claude Code](https://docs.claude.com/en/docs/claude-code/setup).

## Quick start: in the cloud

Nothing to install. One environment works for this repo and for
[mc-mod-version-upgrade](https://github.com/jivinstev/mc-mod-version-upgrade).

1. **Make your copy:** on GitHub, **Use this template → Create a new repository → Private**.
2. **Make the environment (once):** at [claude.ai/code](https://claude.ai/code), open the environment
   menu → **Add environment**. Name it `Minecraft modding`, then:
   - **Network access:** Custom. Tick **Also include default list of common package managers**.
     Paste into **Allowed domains**:
     ```text
     maven.neoforged.net
     *.minecraft.net
     *.mojang.com
     api.modrinth.com
     cdn.modrinth.com
     api.curseforge.com
     *.forgecdn.net
     maven.parchmentmc.org
     maven.fabricmc.net
     maven.blamejared.com
     maven.ithundxr.dev
     dl.cloudsmith.io
     thedarkcolour.github.io
     packages.adoptium.net
     ```
   - **Setup script:** leave it empty.
3. **Start a session** on your copy, in that environment. It opens straight away. Type
   `run ./setup --yes`: it checks every host and installs anything missing (a virtual screen and
   Java 25) the first time, which takes a minute or two. Look for `ready` under
   **6. Cloud environment**.
4. **Let your child say what they want to make.** Claude builds it and runs all three gates.

In the cloud you build and test, and finished work lands on `main` once the gates pass. To play, on
your own computer: clone your copy and run `./setup` once (it finds your Minecraft). After that,
each time: `git pull`, then `./gradlew deployToMods`.
More: [docs/CLOUD.md](docs/CLOUD.md).

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
