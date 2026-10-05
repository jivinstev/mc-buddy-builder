# Building in a Claude Code cloud session

The README has the four steps. This page has the reasons and the fixes.

## What each piece is for

| Piece | Where it lives | Why |
|---|---|---|
| Allowed domains | the environment (UI only) | The build downloads Minecraft and NeoForge (`*.mojang.com`, `*.minecraft.net`, `maven.neoforged.net`). The rest are the mod registries and library mavens that mc-mod-version-upgrade uses, so one environment serves both repos. |
| Setup script | the environment (UI only) | Installs a virtual screen for the real-client test and Java 25 for Minecraft 26.x. It runs once and is cached for later sessions. |
| `cloud/session_start.sh` | this repo, run by `.claude/settings.json` | Points Gradle at Google's mirror of Maven Central, which doesn't rate-limit cloud machines. Does nothing on your own computer. |
| `cloud/check.py` | this repo, run by `./setup` | Checks the two above actually took effect, and names any blocked host. |

The README's copies of the domain list and setup script must match `cloud/allowed-domains.txt` and
`cloud/setup.sh`; CI fails if they drift (`python3 cloud/check_readme.py`).

## Things to know

- **One repo per session.** Claude Code skips a repo's session hooks when a session has several
  repos attached. Start one session per repo.
- **Changing the setup script or domains rebuilds the cache.** The next new session runs the script
  again (a few minutes).
- **You can't play in the cloud.** There's no Minecraft to deploy into. Pull your copy and run
  `./gradlew deployToMods` at home.
- **Making your own copy.** In the cloud, GitHub access is limited to the repos attached to the
  session, so `./setup` can't create a repo for you there. Use **Use this template** on GitHub
  instead.
