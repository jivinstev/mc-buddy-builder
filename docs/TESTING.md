# Testing: why "it's done" isn't enough

In Buddy Builder mode the child can't read the code, so the tests are the review. Four rules came out
of months of building mods this way, each because something passed every check and was still broken.

## The three gates

| Gate | What runs | What it can see | Typical cost |
|---|---|---|---|
| **A** | Plain unit tests | Logic: maths, rules, state machines | seconds |
| **B** | Headless game-test server (`./gradlew runGameTestServer`) | Loading, registration, server behaviour, saving and loading | minutes |
| **C** | A real Minecraft client, driven by a test inside the game | What the player sees and hears: rendering, sound, menus, singleplayer-only paths | 1–5 minutes a test |

Each gate catches what the one before it can't. A feature that touches anything the child will see
or hear needs all three.

### Gate A: keep decisions out of Minecraft

Put every decision that can be expressed without Minecraft into a plain class and unit-test it:
a prize wheel's odds, a mob's power score, how far a jump goes. Those tests run in milliseconds, so
the agent can check its work constantly. The Minecraft-facing code just carries out the answer.

### Gate B: prove it loads and runs

A game test boots a real dedicated server with the mod, spawns things, uses items and saves the
world. It catches crashes that compile perfectly: registering things in the wrong order, reading a
config before it exists, a mob missing an attribute it needs to attack.

**Read the log, not the exit code.** The game-test task can exit 0 having run nothing (a mod failed
to load, or another run held the world lock). Look for `N required tests passed`. Don't match on the
word `All`: Minecraft prints it on a pass and not on a failure.

### Gate C: play it for real

A client test is a small state machine inside the game: create a world, run the feature the way a
player would (a real command, a real right-click), then check the world and write PASS or FAIL. It
is the only gate that can see sounds, rendering, menus and anything that only happens in
singleplayer. Run it on a machine with a display, or on Linux under `xvfb-run` with software
OpenGL.

Two things that make client tests trustworthy:
- **Stop the game pausing.** Singleplayer pauses when its window loses focus, which turns into a
  handful of unrelated-looking failures. A small client-side guard that clears the option and closes
  the pause menu during tests fixes it for every test at once.
- **Write a verdict file and wait on it**, with a timeout that says *no verdict* rather than *failed*.
  A client that crashed and a client that never started look identical otherwise.

## The four rules

1. **A green check is a claim.** Make each check prove it ran: count what it looked at, and fail when
   it looked at nothing.
2. **Reproduce first.** For a "the player sees or hears X" bug, make the client test fail on the bug
   before fixing it. A test that has never failed has never been shown to work.
3. **Look at the screenshot.** A camera pointed the wrong way, a dark room, a texture missing: every
   one of these produces a plausible picture and a PASS. Open the image.
4. **Test where it runs.** A rule tested only where it's defined isn't tested where it runs. If the
   child sees it, a client has to see it.

## Before handing a feature to the child

- [ ] Gate A green
- [ ] Gate B green, and the log says how many tests passed
- [ ] Gate C green for anything visible or audible, and you looked at the screenshots
- [ ] Synced with main and re-tested after the merge
- [ ] The deployed jar contains the new classes
- [ ] The grown-up knows to restart Minecraft

## Coming next

A starter NeoForge mod with all three gates already wired up, including the pause guard, a photo
helper and a Linux launcher, is planned for this repo.
