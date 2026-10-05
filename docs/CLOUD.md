# Building in a Claude Code cloud session

The README has the steps. This page has the reasons and the fixes.

## What each piece is for

| Piece | Where it lives | Why |
|---|---|---|
| Allowed domains | the environment (UI only) | The build downloads Minecraft and NeoForge (`*.mojang.com`, `*.minecraft.net`, `maven.neoforged.net`). The rest are the mod registries and library mavens that mc-mod-version-upgrade uses, so one environment serves both repos. |
| Setup script | the environment (UI only) | **Empty, on purpose.** A setup script blocks the session from opening, and its cache did not reliably hold, so it cost minutes every time. |
| `cloud/ensure.sh` | this repo | Installs a virtual screen (for the real-client test) and Java 25 (for Minecraft 26.x) if they are missing. A minute or two, once per session. `./setup`, `tools/gate-b.sh` and `tools/client-test.sh` call it; a lock makes a second run wait for the first. |
| `cloud/session_start.sh` | this repo, run by `.claude/settings.json` | Starts `cloud/ensure.sh` in the background (log: `/tmp/cloud-ensure.log`) so the tools are usually ready before you need them, and points Gradle at Google's mirror of Maven Central, which doesn't rate-limit cloud machines. Returns at once. Does nothing on your own computer. |
| `cloud/check.py` | this repo, run by `./setup` | Checks every allowed host is reachable, runs `cloud/ensure.sh`, and names anything still missing. |

The README's copy of the domain list must match `cloud/allowed-domains.txt`; CI fails if they
drift (`python3 cloud/check_readme.py`).

## Things to know

- **One repo per session.** Claude Code skips a repo's session hooks when a session has several
  repos attached. Start one session per repo.
- **Changing the domains needs a new session.** A running session keeps the list it started with.
- **The first build is the slow part** (several minutes): Gradle downloads and decompiles Minecraft.
  Nothing can usefully do that ahead of time without blocking the session, so it happens on first build.
- **You can't play in the cloud.** There's no Minecraft to deploy into. When the gates pass, the
  session opens a pull request and merges it into `main` on its own. At home: `git pull`, then
  `./gradlew deployToMods`.
- **Making your own copy.** In the cloud, GitHub access is limited to the repos attached to the
  session, so `./setup` can't create a repo for you there. Use **Use this template** on GitHub
  instead.
