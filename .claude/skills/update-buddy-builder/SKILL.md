---
name: update-buddy-builder
description: Bring in the latest Buddy Builder improvements (the mode, the guardrails, the test tools) from the upstream repo. Use only when the grown-up asks to update Buddy Builder.
---

# Update Buddy Builder

This is a grown-up task. Talk to the grown-up in plain sentences, not kid mode.

`./setup` brings in updates by itself when they merge cleanly and the mod still builds. This skill is
for when it couldn't: a conflict, unsaved changes, or a build that broke.

1. Check the `upstream` remote exists: `git remote -v`. If it doesn't, add it:
   `git remote add upstream https://github.com/jivinstev/mc-buddy-builder.git`.
2. Start from a clean tree on a new branch: `git fetch origin` and `git fetch upstream`. If an
   earlier update left `.worktrees/update` or the `chore/update-buddy-builder` branch behind, clear
   them first: `git worktree remove .worktrees/update`, then `git branch -d chore/update-buddy-builder`.
   If either refuses (unsaved or unmerged work in it), stop and ask the grown-up; never force it.
   Then `git worktree add .worktrees/update -b chore/update-buddy-builder origin/main` and
   `cd .worktrees/update`. Keep worktrees inside the project; anything outside it prompts for permission.
3. `git merge upstream/main`. Expect conflicts only where the family changed a Buddy Builder file
   (the mode, the tools, the starter Bounce Block). Keep the family's own mod code and names;
   take upstream's tools and docs unless the grown-up says otherwise. If unsure, ask.
4. If the mod was renamed, upstream may bring back starter files under the old `buddymod` name.
   Delete those copies; the family's renamed versions are the real ones.
5. Run every gate for the family's version: `./gradlew build`, `./tools/gate-b.sh`,
   `./tools/client-test.sh`. All three must pass before merging.
6. Tell the grown-up what changed (`git log --oneline origin/main..HEAD`), then merge to main with
   the usual workflow (`git push origin HEAD:main`).
7. Clean up, so the next update starts fresh: `cd ../..` (back to the project folder), then
   `git worktree remove .worktrees/update` and `git branch -d chore/update-buddy-builder`.
8. Bring the project folder itself up to date, if it is on `main` with no unsaved changes:
   `git fetch origin` and `git merge --ff-only origin/main`. (If it can't fast-forward, leave it and
   tell the grown-up.) Then tell the grown-up to start a **new** Claude session: the Buddy Builder
   mode is read when a session starts.
