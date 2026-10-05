#!/usr/bin/env python3
"""Claude Code SessionStart hook: tells the session what state this project is in.
Whatever this prints is added to the session's context. It never blocks."""
import os, re

root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
notes = []
try:
    props = open(os.path.join(root, 'gradle.properties'), encoding='utf-8').read()
    if re.search(r'(?m)^mod_id=buddymod\s*$', props):
        notes.append('The mod still has the starter name ("Buddy Mod"). Before building anything, ask '
                     'the child what their mod is called and run /name-my-mod.')
except OSError:
    pass
env = os.path.join(root, '.env.local')
if not os.path.isfile(env):
    notes.append('There is no .env.local yet, so no Minecraft version or mods folder is chosen. '
                 'Ask the grown-up to run ./setup in a terminal (it asks a few questions).')
else:
    text = open(env, encoding='utf-8').read()
    m = re.search(r'(?m)^MC_TARGET=(.+)$', text)
    if m:
        notes.append('This family plays Minecraft %s. Build, test and deploy for that version.' % m.group(1).strip())
if notes:
    print('Buddy Builder project status:\n- ' + '\n- '.join(notes))
