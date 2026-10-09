# Sharing one project between several sessions

It's common to have more than one Claude Code session building for the same child: one making a
dragon while another fixes yesterday's castle. Buddy Builder uses one worktree and one branch per
feature, and three sync points, so that nobody's work is lost.

## One feature, one branch, one worktree

```bash
git fetch origin
git worktree add .worktrees/dragon -b feat/dragon origin/main
cd .worktrees/dragon
```

Worktrees live in `.worktrees/`, inside the project (git ignores that folder). Claude Code asks
permission for anything outside the folder a session started in, so a worktree next to the project
(`../mymod-dragon`) would stop the child's session with prompts it can't answer. The build finds
`.env.local` in the main project folder, so a worktree doesn't need its own copy.

Never work on `main` directly, and never on a branch another worktree has checked out. Keep the
worktree after the feature lands, so the child can ask for changes to it later.

## The three sync points

1. **Before writing any code:** `git fetch origin && git merge origin/main`. Skipping this is how a
   branch drifts dozens of commits behind and new code gets written against a stale project.
2. **After tests are green, before deploying:** merge main in again and re-run the tests. A merge can
   break a green branch. Then deploy, and check the jar in the mods folder contains your new classes,
   because other sessions deploy to the same folder.
3. **After the child has played it:** merge main in once more, then `git push origin HEAD:main` from
   your branch. If the push is rejected, fetch, merge, re-test and push again.

## No `git stash`

The stash is shared between worktrees, so `git stash pop` can take another session's work. Use a
temporary commit instead. `.claude/settings.json` denies `git stash` outright.

## Deploying safely while the game is running

Minecraft holds its mod jars open and reads them lazily. Overwriting a jar in place while the game is
running produces errors that look like code bugs (`ZipException`, classes that loaded a minute ago
going missing). Copy to a temporary file in the mods folder, then move it into place, and restart the
game to load the new build.
