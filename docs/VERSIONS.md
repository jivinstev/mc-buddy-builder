# One project, two Minecraft versions

The starter builds for Minecraft **1.21.1** and **26.2** from one source tree. Your family only needs
the version you play; `./setup` records it as `MC_TARGET` in `.env.local`, and every build, test and
deploy uses it. To build the other one: `./gradlew build -Pmc=1.21.1` (or `-Pmc=26.2`).

## How it works

```text
src/main/java  --[ versions/<version>.renames.tsv ]-->  build/generated/sources/<mc21|mc26>
               --[ src/mc21/java or src/mc26/java replaces whole files ]-->  compiled
```

There are two kinds of version difference, and each has one home:

| Kind | Example | Where it goes |
|---|---|---|
| A **name** changed, the code didn't | `ResourceLocation` became `Identifier` in 26.2 | A row in `versions/26.2.renames.tsv`, after the last `#!strict` line |
| The **code** is different | 1.21.1 bounces with a hook; 26.2 with a coefficient | A class with the same name in both `src/mc21/java` and `src/mc26/java` (a "compat pair") |

Everything else is written once in `src/main/java`. Never write `if (version == ...)` in shared code.

`versions/<version>.properties` holds the Minecraft, NeoForge and Java versions. Minecraft 26.2 needs
Java 25; the build downloads it if your computer only has 21.

## Things that only happen on 26.2

- `@GameTest` doesn't exist in 26.2. Keep writing tests with it in shared code;
  `tools/buddy/gametest_adapter.py` wires them up for 26.2 at build time.
- Every build prints a **dead-rule check**. A rename row that matches nothing is either unused or
  broken, and the check says which rows those are. Rows above the last `#!strict` line came from a
  much bigger mod and are expected to be mostly unused.

## Where the rules came from

The pipeline and the rename table come from
[mc-mod-version-upgrade](https://github.com/jivinstev/mc-mod-version-upgrade), which ported a large
mod across these two versions. Its catalogue explains each 26.2 change in detail.
