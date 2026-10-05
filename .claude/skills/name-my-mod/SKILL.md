---
name: name-my-mod
description: Give the mod its own name (rename it from the starter's "Buddy Mod"). Use when the child or grown-up wants to name or rename their mod, or when the session start says the mod still has the starter name.
---

# Name the mod

1. Ask the child what their mod is called, in one short, excited question. Offer two or three fun
   ideas from what they have been building if they're stuck. Any name is fine; it only needs a
   letter in it.
2. Check what the name becomes, without changing anything:
   `python3 tools/buddy/rename_mod.py "<the name>" --dry-run`
   If the tool refuses the name, say why in kid words and ask again.
3. Make sure nothing is half-finished: `git status` must be clean (commit work in progress first).
   Then rename for real: `python3 tools/buddy/rename_mod.py "<the name>"`.
4. Delete `build/` and `run/` (they hold the old name), then run Gate A and Gate B
   (`./gradlew build` and `./tools/gate-b.sh`). Both must pass.
5. If a jar with the OLD name is in the mods folder, remove it so two copies don't load. Then
   `./gradlew deployToMods`.
6. Commit on a branch: `Name the mod <the name>`. Follow the usual workflow to merge it.
7. Tell the child: "Your mod is called <the name> now!" Remind the grown-up to restart Minecraft.
