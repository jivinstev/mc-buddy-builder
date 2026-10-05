#!/usr/bin/env python3
"""Claude Code PreToolUse hook: the mod gets its name before anything is built.

While gradle.properties still says mod_id=buddymod, editing the mod's own files (src/, art/) is
refused, and the reason tells Claude to ask the child for a name and run /name-my-mod. The
rename itself runs through Bash (tools/buddy/rename_mod.py), so it is never blocked.

Two ways past it, both deliberate:
  KEEP_STARTER_NAME=yes in .env.local   the family chose to keep "Buddy Mod"
  BUDDY_MAINTAINER=1 in the environment  someone working on Buddy Builder's own starter mod
Exit 0 allows, exit 2 refuses (Claude Code shows stderr to Claude). Never fails closed on a bug:
anything unexpected allows, because a broken guard must not stop a child's session cold."""
import json, os, re, sys

GUARDED = ('src', 'art')
REASON = ('The mod still has the starter name ("Buddy Mod"), so its files stay unchanged until it has '
          'its own name. Ask the child what their mod is called (one short, excited question), then '
          'run /name-my-mod. If the family wants to keep "Buddy Mod", add KEEP_STARTER_NAME=yes to '
          '.env.local.')


def blocked(root, path, env):
    if env.get('BUDDY_MAINTAINER') == '1' or not path:
        return False
    try:
        props = open(os.path.join(root, 'gradle.properties'), encoding='utf-8').read()
    except OSError:
        return False
    if not re.search(r'(?m)^mod_id=buddymod\s*$', props):
        return False
    try:
        if re.search(r'(?m)^KEEP_STARTER_NAME=yes\s*$', open(os.path.join(root, '.env.local'), encoding='utf-8').read()):
            return False
    except OSError:
        pass
    rel = os.path.relpath(os.path.abspath(os.path.join(root, path)), root)
    return rel.split(os.sep)[0] in GUARDED


def main():
    try:
        event = json.load(sys.stdin)
        inp = event.get('tool_input') or {}
        path = inp.get('file_path') or inp.get('notebook_path') or ''
        root = os.environ.get('CLAUDE_PROJECT_DIR') or event.get('cwd') or os.getcwd()
        if blocked(root, path, os.environ):
            print(REASON, file=sys.stderr)
            return 2
    except Exception:
        pass
    return 0


if __name__ == '__main__':
    sys.exit(main())
