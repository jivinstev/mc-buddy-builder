#!/usr/bin/env python3
"""Making a mod must never stop for an approval prompt.

    python3 tools/buddy/test_permissions.py          # static: CI, no Claude needed
    python3 tools/buddy/test_permissions.py --live   # real headless Claude Code, default mode

Static: every command the mod-making workflow uses (WORKFLOW below) must match an `allow` rule in
.claude/settings.json and no `ask` or `deny` rule, and every script an allow rule names must exist
(a renamed script would otherwise start prompting with nothing failing).

Live: runs `claude -p` in DEFAULT permission mode (the strictest; auto mode only ever asks less),
has it run harmless commands and edit a file, and fails if Claude Code refused any of them. A
control (`curl`, which is not allowed) must be refused, or the probe cannot see a prompt at all.
Needs `claude` installed and this folder trusted (run `claude` here once and accept the dialog:
until then Claude Code ignores the repo's allow rules, which is itself worth knowing).

Matching follows what was measured against Claude Code, not what one might guess:
  - `Bash(x:*)` matches `x` followed by a space or the end, not `x` as a bare string prefix:
    `Bash(python3 tools/:*)` did NOT allow `python3 tools/buddy/test_setup.py`.
  - a leading `MC=26.2 ` is NOT stripped, so those forms need rules of their own.
"""
import json, pathlib, re, shutil, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
SETTINGS = ROOT / '.claude/settings.json'

# What making a mod actually runs: the output style, the skills, the README and docs.
WORKFLOW = [
    './setup --yes', './setup --check',
    './gradlew build', './gradlew build -Pmc=1.21.1', './gradlew -Pmc=26.2 build', './gradlew deployToMods',
    './tools/gate-b.sh', 'MC=1.21.1 ./tools/gate-b.sh', 'MC=26.2 ./tools/gate-b.sh',
    './tools/client-test.sh', 'MC=1.21.1 ./tools/client-test.sh', 'MC=26.2 ./tools/client-test.sh',
    'python3 tools/buddy/rename_mod.py --name "Dragon Mod"', 'python3 tools/buddy/test_rename_mod.py',
    'python3 tools/buddy/test_setup.py', 'python3 tools/buddy/test_name_guard.py', 'python3 tools/check-private-terms.py --staged',
    'python3 tools/buddy/make_texture.py art/dragon.txt src/main/resources/assets/buddymod/textures/block/dragon.png',
    'python3 tools/buddy/test_make_texture.py',
    'python3 cloud/check.py', 'bash cloud/ensure.sh java25',
    'git status', 'git diff', 'git log --oneline -5', 'git add -A', 'git commit -m "Add a dragon"',
    'git push -u origin dragon', 'git pull', 'git switch -c dragon', 'git branch', 'git merge main',
    'git worktree list', 'git worktree add .worktrees/dragon -b feat/dragon origin/main',
    'unzip -l mods/buddymod-1.0.jar',
]
# Things that must still stop: a grown-up decides.
MUST_STOP = ['git push --force origin main', 'git reset --hard', 'git stash', 'sudo apt-get install x']


def rules(kind):
    return json.loads(SETTINGS.read_text())['permissions'].get(kind, [])


def bash_match(rule, cmd):
    if not (rule.startswith('Bash(') and rule.endswith(')')):
        return False
    body = rule[5:-1]
    if body.endswith(':*'):
        p = body[:-2]
        return cmd == p or cmd.startswith(p + ' ')
    return cmd == body


def static():
    fails = []
    allow, ask, deny = rules('allow'), rules('ask'), rules('deny')
    for c in WORKFLOW:
        if not any(bash_match(r, c) for r in allow):
            fails.append('no allow rule for: ' + c)
        if any(bash_match(r, c) for r in ask + deny):
            fails.append('an ask/deny rule catches: ' + c)
    for c in MUST_STOP:
        if not any(bash_match(r, c) for r in deny):
            fails.append('not denied, but must be: ' + c)
    for r in allow:
        if r.startswith('Bash(') and '*' in r[5:-3]:
            fails.append('wildcard inside a rule can reach any path (use exact scripts): ' + r)
        body = r[5:-1].removesuffix(':*') if r.startswith('Bash(') else ''
        for word in body.split():
            if ('/' in word) and not (ROOT / word).exists():
                fails.append('allow rule names a script that does not exist: ' + r)
    if set(ask) - {'WebFetch', 'WebSearch'}:
        fails.append('unexpected ask rules (each one is a prompt): %s' % sorted(set(ask) - {'WebFetch', 'WebSearch'}))
    if 'Edit(/**)' not in allow:
        fails.append('edits inside the project must be allowed: Edit(/**)')
    # A worktree outside the project (../x) makes every read, edit and build in it ask permission.
    for doc in [ROOT / 'README.md', *ROOT.glob('docs/*.md'), *ROOT.glob('.claude/**/*.md')]:
        for n, line in enumerate(doc.read_text(encoding='utf-8').splitlines(), 1):
            if re.search(r'worktree add\s+\.\.', line):
                fails.append('%s:%d puts a worktree outside the project (use .worktrees/<name>)' % (doc.relative_to(ROOT), n))
    # Test output Claude reads (logs, the Gate C photo) must land inside the project, or reading it
    # stops the session for permission. Scripts write under build/ instead of the temp folder.
    for script in sorted(ROOT.glob('tools/*.sh')):
        for n, line in enumerate(script.read_text(encoding='utf-8').splitlines(), 1):
            if re.search(r'\bmktemp\b|\$\{?TMPDIR|(^|[\s"=])/tmp/', line) and not line.lstrip().startswith('#'):
                fails.append('%s:%d writes outside the project (use build/): %s' % (script.relative_to(ROOT), n, line.strip()))
    if '.worktrees/' not in (ROOT / '.gitignore').read_text().split():
        fails.append('.worktrees/ must be in .gitignore, or `git add -A` picks up worktrees')
    return fails


def live_probe(prompt):
    p = subprocess.run(['claude', '-p', prompt, '--permission-mode', 'default', '--model',
                        'claude-haiku-4-5-20251001', '--output-format', 'stream-json', '--verbose'],
                       cwd=ROOT, capture_output=True, text=True, timeout=300)
    denied, used = [], 0
    for line in p.stdout.splitlines():
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if e.get('type') == 'assistant':
            used += sum(1 for b in e['message'].get('content', []) if b.get('type') == 'tool_use')
        if e.get('type') == 'result':
            denied = e.get('permission_denials', [])
    return used, denied


def live():
    if not shutil.which('claude'):
        return ['--live needs the claude command on PATH']
    fails = []
    cases = [('./setup --check', True), ('python3 tools/buddy/test_rename_mod.py', True),
             ('git status --short', True), ('python3 -c "print(1)"', False)]
    for cmd, should_pass in cases:
        used, denied = live_probe('Use the Bash tool exactly once to run this command, then stop: ' + cmd)
        if not used:
            fails.append('probe did not even try: ' + cmd)
        elif should_pass and denied:
            fails.append('needed approval: ' + cmd)
        elif not should_pass and not denied:
            fails.append('control was NOT refused (the probe cannot see prompts): ' + cmd)
        print('  %-45s %s' % (cmd, 'refused' if denied else 'ran'))
    for probe_file in ['build/permission-probe.txt', '.worktrees/permission-probe/docs/probe.txt']:
        used, denied = live_probe('Use the Write tool exactly once to create %s containing the word ok, then stop.' % probe_file)
        (ROOT / probe_file).unlink(missing_ok=True)
        if not used or denied:
            fails.append('editing %s needed approval (or was not tried)' % probe_file)
        print('  %-45s %s' % ('Write ' + probe_file, 'refused' if denied else 'ran'))
    shutil.rmtree(ROOT / '.worktrees/permission-probe', ignore_errors=True)
    return fails


def main():
    fails = static()
    if '--live' in sys.argv:
        fails += live()
    for f in fails:
        print('  FAIL ' + f)
    print('test_permissions: %s' % ('PASS' if not fails else 'FAIL (%d)' % len(fails)))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
