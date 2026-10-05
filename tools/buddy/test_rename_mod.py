#!/usr/bin/env python3
"""Renames a throwaway copy of the repo and checks nothing still carries the old name.

    python3 tools/buddy/test_rename_mod.py
"""
import os, shutil, subprocess, sys, tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


def copy_repo(dst):
    def ignore(d, names):
        return [n for n in names if n in ('.git', 'build', 'run', '.gradle', '__pycache__')]
    shutil.copytree(ROOT, dst, ignore=ignore)


def run(cwd, *args):
    return subprocess.run([sys.executable, *args], cwd=cwd, capture_output=True, text=True)


def leftovers(root, needles):
    hits = []
    for rel in ('src', 'gradle.properties', 'settings.gradle'):
        base = os.path.join(root, rel)
        paths = [base] if os.path.isfile(base) else [os.path.join(dp, f) for dp, _, fs in os.walk(base) for f in fs]
        for p in paths:
            r = os.path.relpath(p, root)
            if any(n in r for n in needles):
                hits.append('path ' + r)
            try:
                text = open(p, encoding='utf-8').read()
            except UnicodeDecodeError:
                continue
            for n in needles:
                if n in text:
                    hits.append('%s contains %r' % (r, n))
    return hits


def main():
    old_id = [l.split('=', 1)[1].strip() for l in open(os.path.join(ROOT, 'gradle.properties'))
              if l.startswith('mod_id=')][0]
    fails = []
    with tempfile.TemporaryDirectory() as t:
        repo = os.path.join(t, 'repo')
        copy_repo(repo)
        tool = os.path.join(repo, 'tools/buddy/rename_mod.py')
        for bad in ['', '123', 'ab', 'Minecraft']:
            r = run(repo, tool, bad, '--dry-run')
            if r.returncode != 2:
                fails.append('a bad name %r was accepted' % bad)
        r = run(repo, tool, 'Dragon Treasure')
        if r.returncode != 0:
            fails.append('rename failed: ' + r.stdout + r.stderr)
        else:
            left = leftovers(repo, [old_id])
            fails += ['old name left behind: ' + h for h in left]
            props = open(os.path.join(repo, 'gradle.properties')).read()
            for want in ('mod_id=dragontreasure', 'mod_name=Dragon Treasure', 'mod_group_id=com.dragontreasure'):
                if want not in props:
                    fails.append('gradle.properties is missing ' + want)
            if not os.path.isfile(os.path.join(repo, 'src/main/java/com/dragontreasure/DragonTreasureMod.java')):
                fails.append('main class was not renamed to DragonTreasureMod')
            lang = open(os.path.join(repo, 'src/main/resources/assets/dragontreasure/lang/en_us.json')).read()
            if '"itemGroup.dragontreasure": "Dragon Treasure"' not in lang:
                fails.append('creative tab name not updated: ' + lang)
            # The renamed tree must still prepare for both versions.
            for t_, o in (('1.21.1', 'mc21'), ('26.2', 'mc26')):
                args = ['tools/buddy/prepare-sources.py', '--src', 'src/main/java', '--overlay', 'src/%s/java' % o,
                        '--renames', 'versions/%s.renames.tsv' % t_, '--out', os.path.join(t, 'out-' + t_)]
                if t_ == '26.2':
                    args += ['--gametest-adapter', 'dragontreasure', '--gametest-pkg', 'com.dragontreasure.compat']
                r2 = run(repo, *args)
                if r2.returncode != 0:
                    fails.append('prepare-sources failed for %s after the rename: %s' % (t_, r2.stderr[-500:]))
            r3 = run(repo, tool, 'Dragon Treasure')
            if r3.returncode == 0:
                fails.append('renaming to the same name twice should do nothing and say so')
            r4 = run(repo, tool, 'Lava Pets')
            if r4.returncode != 0 or leftovers(repo, ['dragontreasure', 'DragonTreasure']):
                fails.append('a second rename did not take cleanly')
    if fails:
        print('test_rename_mod: FAIL')
        for f in fails:
            print('  - ' + f)
        return 1
    print('test_rename_mod: PASS')
    return 0


if __name__ == '__main__':
    sys.exit(main())
