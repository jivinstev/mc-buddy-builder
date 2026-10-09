#!/usr/bin/env python3
"""Runs ./setup against a fake home folder and a throwaway copy of the repo.

    python3 tools/buddy/test_setup.py

Checks that an existing NeoForge install is found and recommended, that the default with no
install is the newest version, that a re-run with --yes changes nothing, and that 'local'
keeps Buddy Builder reachable as `upstream`, and that with no keyboard (Claude running it) plain
./setup finishes like --yes.
"""
import json, os, pathlib, shutil, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent


def repo_copy(dst):
    # A fresh repo, never a copy of .git: in a worktree .git is a pointer to the real repository,
    # and setup renaming the copy's remotes would rename the real ones.
    shutil.copytree(ROOT, dst, ignore=lambda d, n: [x for x in n if x in (
        '.git', '.worktrees', 'build', 'run', '.gradle', '__pycache__', '.env.local', '.env.local.bak')])
    subprocess.run(['git', 'init', '-q'], cwd=dst, check=True)
    subprocess.run(['git', 'remote', 'add', 'origin', 'https://github.com/jivinstev/mc-buddy-builder.git'], cwd=dst, check=True)


def setup(repo, home, *args, cloud=False):
    env = dict(os.environ, HOME=str(home), XDG_DATA_HOME=str(home / '.local/share'), BUDDY_SETUP_OFFLINE='1')
    env.pop('MINECRAFT_DIR', None)
    env.pop('CLAUDE_CODE_REMOTE', None)
    if cloud:
        env['CLAUDE_CODE_REMOTE'] = 'true'
    # No keyboard, like Claude Code's own shell (and CI).
    return subprocess.run([sys.executable, 'tools/buddy/setup.py', *args], cwd=repo, env=env,
                          capture_output=True, text=True, stdin=subprocess.DEVNULL)


def env_of(repo):
    p = pathlib.Path(repo) / '.env.local'
    return dict(l.split('=', 1) for l in p.read_text().splitlines() if '=' in l and not l.startswith('#')) if p.exists() else {}


def main():
    fails = []
    with tempfile.TemporaryDirectory() as t:
        t = pathlib.Path(t)
        # 1. No Minecraft at all: recommend the newest supported version and no mods folder.
        home = t / 'empty-home'; home.mkdir()
        repo = t / 'a'; repo_copy(repo)
        r = setup(repo, home, '--yes', '--repo', 'local')
        e = env_of(repo)
        if r.returncode != 0:
            fails.append('setup failed with no Minecraft: ' + r.stdout[-800:] + r.stderr[-800:])
        elif e.get('MC_TARGET') != '26.2' or any(k.startswith('MINECRAFT_MODS_DIR') for k in e):
            fails.append('with no install it should pick 26.2 and no mods folder, got %s' % e)
        remotes = subprocess.run(['git', 'remote'], cwd=repo, capture_output=True, text=True).stdout.split()
        if 'upstream' not in remotes or 'origin' in remotes:
            fails.append('"local" should leave only an upstream remote, got %s' % remotes)

        # 2. A Prism instance running NeoForge for 1.21.1: that version is the recommendation. The
        #    mods folder is still the Buddy Builder launcher profile's, which a test run never installs.
        home = t / 'prism-home'
        prism = 'Library/Application Support/PrismLauncher' if sys.platform == 'darwin' else '.local/share/PrismLauncher'
        inst = home / prism / 'instances/My Pack'
        (inst / '.minecraft/mods').mkdir(parents=True)
        (inst / '.minecraft/mods/some-mod.jar').write_bytes(b'')
        (inst / 'mmc-pack.json').write_text(json.dumps({'components': [
            {'uid': 'net.minecraft', 'version': '1.21.1'},
            {'uid': 'net.neoforged', 'version': '21.1.228'}]}))
        repo = t / 'b'; repo_copy(repo)
        r = setup(repo, home, '--yes', '--repo', 'local')
        e = env_of(repo)
        if r.returncode != 0:
            fails.append('setup failed with a Prism install: ' + r.stdout[-800:] + r.stderr[-800:])
        elif e.get('MC_TARGET') != '1.21.1' or 'MINECRAFT_MODS_DIR_1_21_1' in e:
            fails.append('it should recommend 1.21.1 and install nothing offline, got %s' % e)
        elif 'skipped (BUDDY_SETUP_OFFLINE)' not in r.stdout:
            fails.append('offline, setup must say what it skipped:\n' + r.stdout[-800:])

        # 3. A re-run with --yes changes nothing.
        before = (repo / '.env.local').read_text()
        r = setup(repo, home, '--yes')
        if r.returncode != 0 or (repo / '.env.local').read_text() != before or 'already up to date' not in r.stdout:
            fails.append('a second --yes run changed something:\n' + r.stdout[-800:])

        # 4. A hand edit wins over a recommendation on a re-run.
        (repo / '.env.local').write_text(before.replace('MC_TARGET=1.21.1', 'MC_TARGET=26.2'))
        r = setup(repo, home, '--yes')
        if 'MC_TARGET=26.2' not in (repo / '.env.local').read_text():
            fails.append('a re-run overwrote a hand-edited MC_TARGET')

        # 4b. --mods-dir is used as given, and nothing is installed for it.
        mods = t / 'my-instance/mods'; mods.mkdir(parents=True)
        r = setup(repo, home, '--yes', '--mods-dir', str(mods))
        if env_of(repo).get('MINECRAFT_MODS_DIR_26_2') != str(mods):
            fails.append('--mods-dir was not written:\n' + r.stdout[-600:])
        # 5. --name renames the mod; --check changes nothing.
        repo = t / 'c'; repo_copy(repo)
        r = setup(repo, t / 'empty-home', '--check', '--repo', 'local')
        if (repo / '.env.local').exists() or 'would' not in r.stdout:
            fails.append('--check wrote something or did not report:\n' + r.stdout[-600:])
        r = setup(repo, t / 'empty-home', '--yes', '--repo', 'local', '--name', 'Lava Pets')
        if 'mod_id=lavapets' not in (repo / 'gradle.properties').read_text():
            fails.append('--name did not rename the mod:\n' + r.stdout[-600:])
        # 6. In a cloud session: never touch the remotes, and report on the environment.
        repo = t / 'd'; repo_copy(repo)
        r = setup(repo, t / 'empty-home', '--yes', cloud=True)
        remotes = subprocess.run(['git', 'remote'], cwd=repo, capture_output=True, text=True).stdout.split()
        if remotes != ['origin'] or '6. Cloud environment' not in r.stdout:
            fails.append('in the cloud, setup must leave origin alone and check the environment:\n' + r.stdout[-600:])
        # 7. Plain ./setup with no keyboard (the README's cloud step: Claude runs it, nobody can
        #    answer): take every recommendation, as --yes does, instead of stopping at question 1.
        repo = t / 'e'; repo_copy(repo)
        r = setup(repo, t / 'empty-home', cloud=True)
        if r.returncode != 0 or env_of(repo).get('MC_TARGET') != '26.2' or 'Next:' not in r.stdout:
            fails.append('plain ./setup with no keyboard must finish like --yes (exit %d):\n%s'
                         % (r.returncode, r.stdout[-600:]))
    if fails:
        print('test_setup: FAIL')
        for f in fails:
            print('  - ' + f)
        return 1
    print('test_setup: PASS')
    return 0


if __name__ == '__main__':
    sys.exit(main())
