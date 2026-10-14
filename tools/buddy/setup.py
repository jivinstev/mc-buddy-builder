#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""First-run setup for a Buddy Builder mod. Usually run as `./setup`.

    ./setup                  asks each question with a recommendation; Enter accepts it
                             (on Windows, from PowerShell: .\\setup.cmd, with the same options)
    ./setup --yes            take every recommendation (re-run: keep every earlier answer)
    ./setup --check          change nothing; say what setup would do
    ./setup --target 1.21.1 --mods-dir ~/path/mods --name "Dragon Treasure" --repo private

WHAT IT DOES
    0. Brings in Buddy Builder updates, if there are any (asking first). It merges `upstream/main`
       into your main, checks the mod still builds, pushes, and starts setup again with the new
       version. Anything it can't do safely (a conflict, unsaved changes, a failed build) it undoes,
       and tells you to ask Claude to run /update-buddy-builder instead.
    1. Checks the tools, and installs what's missing (asking first): Java 21 (into this user's own
       folder: no password or administrator prompt), Claude Code, and the GitHub CLI. On a Mac,
       Claude Code comes from its installer and gh from Homebrew; git and Python come with the Mac's
       developer tools. On Windows, Claude Code and gh come from winget (install.ps1 has already
       installed git and Python the same way), and setup also gives Git Bash a `python3` command,
       points Claude Code at the real Python, and checks long paths and the Administrator window.
    2. Picks the Minecraft version (the newest this mod supports, unless an install here already
       runs NeoForge on a supported one), then gets Minecraft ready to play it: NeoForge, and a
       "Buddy Builder (<version>)" profile in the Minecraft launcher with its own game folder, so
       the family's normal worlds are untouched (tools/buddy/install_game.py). That profile's mods
       folder is where the mod is installed. --mods-dir uses a mods folder of your own instead.
    3. Names the mod (optional; you can do it later, or let your child pick with /name-my-mod).
    4. Decides where your copy lives:
         private  a new PRIVATE repo on your GitHub account, holding this project (recommended).
                  Updates from Buddy Builder still arrive: `upstream` points back here.
         fork     a PUBLIC fork. GitHub forks of public repos are always public, so anything
                  your child adds is visible to everyone. Choose this only if that is what you want.
         local    no GitHub repo for now. You can run ./setup again later to make one.
    5. Writes .env.local (never committed) and switches on the git hooks.

RE-RUNNING IS SAFE
    It reads .env.local first, and a value you typed in by hand is never overwritten without
    asking. --yes on a re-run keeps what is there. .env.local is backed up to .env.local.bak
    before every write. Nothing is ever deleted.

Standard library only.
"""
import argparse, json, os, pathlib, platform, re, shutil, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
ENV = ROOT / '.env.local'
SYS = platform.system()
UPSTREAM = 'jivinstev/mc-buddy-builder'
sys.path.insert(0, str(ROOT / 'tools' / 'buddy'))

# winget searches every source it has, and when the Microsoft Store source fails (0x8a15005e: its
# certificate pinning, behind TLS inspection or on a VM with a wrong clock) it installs nothing at all.
# Nothing here needs the Store, so every winget line names its source.
WINGET = ['winget', 'install', '-e', '--source', 'winget', '--accept-package-agreements',
          '--accept-source-agreements', '--id']
HINTS = {
    'git': {'Darwin': 'xcode-select --install', 'Windows': 'winget install -e --source winget --id Git.Git',
            'Linux': 'sudo apt install git'},
    'java': {'Darwin': 'brew install --cask temurin@21', 'Windows': 'run setup again and answer yes to Java 21',
             'Linux': 'sudo apt install openjdk-21-jdk'},
    'claude': {'Darwin': 'https://docs.claude.com/en/docs/claude-code/setup',
               'Windows': 'winget install -e --source winget --id Anthropic.ClaudeCode',
               'Linux': 'https://docs.claude.com/en/docs/claude-code/setup'},
    'gh': {'Darwin': 'brew install gh', 'Windows': 'winget install -e --source winget --id GitHub.cli',
           'Linux': 'https://cli.github.com'},
}
# What setup runs on Windows to install a missing tool. Only package managers that check what they
# download (winget verifies each installer's hash against its manifest), never a script piped into a shell.
WINGET_IDS = {'claude': 'Anthropic.ClaudeCode', 'gh': 'GitHub.cli'}


CLAUDE_INSTALL = 'curl -fsSL https://claude.ai/install.sh | bash'
# Tests and CI set this: nothing is downloaded or installed, and setup says what it skipped.
OFFLINE = os.environ.get('BUDDY_SETUP_OFFLINE') == '1'


def hint(tool):
    return HINTS[tool].get(SYS, HINTS[tool]['Linux'])


def run(cmd, cwd=ROOT, check=False):
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    except OSError as e:            # not installed, or (Windows) not a program CreateProcess can start
        if check:
            raise SystemExit('setup: `%s` could not start: %s' % (' '.join(cmd), e))
        return 127, str(e)
    if check and p.returncode != 0:
        raise SystemExit('setup: `%s` failed:\n%s' % (' '.join(cmd), p.stdout + p.stderr))
    return p.returncode, ((p.stdout or '') + (p.stderr or '')).strip()


def write_lf(path, text):
    """UTF-8 with LF endings on every OS. Windows text mode would write CRLF, and bash reads these files
    (.env.local, the python3 shim): a trailing \\r there is a broken value or `$'\\r': not found`."""
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)


# ── .env.local ────────────────────────────────────────────────────────────────────────────
def read_env():
    out = {}
    if ENV.is_file():
        for line in ENV.read_text(encoding='utf-8').splitlines():
            m = re.match(r'\s*([A-Za-z_][A-Za-z0-9_]*)\s*=(.*)$', line)
            if m and not line.lstrip().startswith('#'):
                out[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    return out


def write_env(changes):
    lines = ENV.read_text(encoding='utf-8').splitlines() if ENV.is_file() else [
        '# Written by ./setup. Never committed. Edit freely; a hand edit always wins.']
    out, seen = [], set()
    for line in lines:
        m = re.match(r'\s*([A-Za-z_][A-Za-z0-9_]*)\s*=', line)
        if m and not line.lstrip().startswith('#') and m.group(1) in changes:
            out.append('%s=%s' % (m.group(1), changes[m.group(1)]))
            seen.add(m.group(1))
        else:
            out.append(line)
    out += ['%s=%s' % (k, v) for k, v in changes.items() if k not in seen]
    if ENV.is_file():
        shutil.copy2(ENV, ENV.with_name('.env.local.bak'))
    write_lf(ENV, '\n'.join(out) + '\n')


def mods_key(target):
    return 'MINECRAFT_MODS_DIR_' + target.replace('.', '_')


# ── versions and installs ─────────────────────────────────────────────────────────────────
def supported_targets():
    """Every versions/<target>.properties, newest first."""
    ts = [p.stem for p in (ROOT / 'versions').glob('*.properties')]
    return sorted(ts, key=lambda t: [int(x) for x in t.split('.')], reverse=True)


def neoforge_target(loader):
    """`neoforge-21.1.228` -> 1.21.1; `neoforge 26.2.0.75` -> 26.2. None if not NeoForge."""
    m = re.search(r'neoforged?[-_ ]?(\d+)\.(\d+)\.', loader, re.I)
    if not m:
        return None
    a, b = int(m.group(1)), int(m.group(2))
    return '%d.%d' % (a, b) if a >= 26 else ('1.%d' % a + ('.%d' % b if b else ''))


def find_installs():
    import find_minecraft
    return find_minecraft.discover(ENV)


def recommend(installs, targets):
    """(target, mods dir, why). A NeoForge install on a supported version wins; one that
    already has mods in it wins over one that does not."""
    best = None
    for inst in installs:
        for loader in inst.get('loaders', []):
            t = neoforge_target(loader)
            if t in targets:
                score = (1 if inst.get('mods') else 0, targets.index(t) * -1)
                if best is None or score > best[0]:
                    best = (score, t, str(pathlib.Path(inst['path']) / 'mods'),
                            'your %s install already runs NeoForge for Minecraft %s' % (inst['kind'], t))
    if best:
        return best[1], best[2], best[3]
    return targets[0], '', 'the newest version this mod supports (no NeoForge install found)'


# ── asking ────────────────────────────────────────────────────────────────────────────────
class Ask:
    def __init__(self, a):
        self.interactive = not (a.yes or a.check)
        # Claude Code runs ./setup with no keyboard attached: a question would just stop setup.
        if self.interactive and not sys.stdin.isatty():
            # Git Bash's own window (mintty) is a keyboard that Windows Python cannot see as one. A
            # person is there (./setup told us so), and taking every answer for them would install
            # things and make a GitHub repo without asking: stop and say where to run it instead.
            if SYS == 'Windows' and os.environ.get('BUDDY_SETUP_TTY') == '1':
                raise SystemExit('setup: Git Bash\'s window cannot pass your answers to Windows Python. Run it '
                                 'from PowerShell instead:  .\\setup.cmd   (or here: ./setup --yes to take '
                                 'every recommendation without being asked)')
            self.interactive = False
            print('(no keyboard here, so taking every recommendation, as --yes does)')

    def __call__(self, question, default, choices=None):
        if not self.interactive:
            return default
        while True:
            ans = input('  %s [%s]: ' % (question, default or 'none')).strip()
            if not ans:
                return default
            if ans.lower() == 'none':
                return ''
            if choices is None or ans.lower() in choices:
                return ans.lower() if choices else ans
            print('    please answer one of: ' + ', '.join(choices))


# ── repo ──────────────────────────────────────────────────────────────────────────────────
def remotes():
    code, out = run(['git', 'remote', '-v'])
    found = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 2:
            found[parts[0]] = parts[1]
    return found


def is_upstream(url):
    return bool(url) and UPSTREAM in url.replace('.git', '')


def gh_ready():
    if not shutil.which('gh'):
        return False, 'the GitHub CLI is not installed (%s)' % hint('gh')
    code, _ = run(['gh', 'auth', 'status'])
    if code != 0:
        return False, 'the GitHub CLI is not signed in (run `gh auth login`)'
    return True, ''


def set_up_repo(choice, name, dry):
    r = remotes()
    if 'origin' not in r or not is_upstream(r.get('origin')):
        return 'kept: this project already has its own repo (%s)' % r.get('origin', 'no remote')
    if choice == 'skip':
        return 'skipped: origin still points at Buddy Builder itself'
    steps = []
    # The family's copy starts on main, even when Buddy Builder was cloned from another branch:
    # the workflow branches from origin/main and lands work there.
    if run(['git', 'branch', '--show-current'])[1] not in ('main', ''):
        steps.append(['git', 'branch', '-M', 'main'])
    if choice in ('private', 'local'):
        steps.append(['git', 'remote', 'rename', 'origin', 'upstream'])
    if choice == 'private':
        steps.append(['gh', 'repo', 'create', name, '--private', '--source', '.', '--remote', 'origin', '--push'])
    if choice == 'fork':
        steps.append(['gh', 'repo', 'fork', '--remote', '--fork-name', name])
    if dry:
        return 'would run: ' + ' && '.join(' '.join(s) for s in steps)
    for s in steps:
        run(s, check=True)
    return {'private': 'made a private repo "%s"; Buddy Builder updates come from `upstream`' % name,
            'fork': 'made a public fork "%s"; Buddy Builder updates come from `upstream`' % name,
            'local': 'no GitHub repo yet; Buddy Builder updates come from `upstream`'}[choice]


# ── main ──────────────────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--yes', action='store_true', help='take every recommendation')
    ap.add_argument('--check', action='store_true', help='change nothing; report')
    ap.add_argument('--target', help='Minecraft version to build for')
    ap.add_argument('--mods-dir', help='the mods folder of the Minecraft install you play')
    ap.add_argument('--name', help='your mod\'s name, e.g. "Dragon Treasure"')
    ap.add_argument('--repo', choices=['private', 'fork', 'local', 'skip'], help='where your copy lives')
    a = ap.parse_args()
    ask = Ask(a)
    env = read_env()
    cloud = os.environ.get('CLAUDE_CODE_REMOTE') == 'true'
    notes, changes = [], {}

    if update_step(ask, a, cloud):
        # Setup itself may have changed: run the new one, which finds nothing more to update.
        sys.stdout.flush()      # execv drops anything still buffered
        again = [sys.executable, str(pathlib.Path(__file__).resolve())] + sys.argv[1:]
        if SYS == 'Windows':
            # Windows has no real exec: os.execv starts a new process and returns the console to the
            # shell while the new setup still reads the keyboard. Wait for it instead.
            sys.exit(subprocess.call(again))
        os.execv(sys.executable, again)

    print('1. Tools')
    import install_game
    tools_step(ask, a, cloud, notes, install_game)
    if SYS == 'Windows' and not cloud:
        windows_step(ask, a, notes)
        # The build's Python (build.gradle reads PYTHON from .env.local on Windows, when ./gradlew is run
        # from a window Claude Code did not start). A hand edit that still works is kept.
        if not (env.get('PYTHON') and pathlib.Path(env['PYTHON']).is_file()):
            changes['PYTHON'] = pathlib.Path(sys.executable).as_posix()

    print('2. Minecraft')
    targets = supported_targets()
    installs = find_installs()
    for inst in installs:
        mods = 'no mods folder' if inst.get('mods') is None else '%d mods' % inst['mods']
        print('   found %s: %s (%s; %s)' % (inst['kind'], inst['path'],
                                          ', '.join(inst.get('loaders') or inst.get('versions') or ['?']), mods))
    if not installs:
        print('   no Minecraft install found here. That is fine for building and testing.')
    rec_t, _, why = recommend(installs, targets)
    if env.get('MC_TARGET') in targets:
        rec_t, why = env['MC_TARGET'], 'your earlier choice'
    print('   supported versions: %s. Recommended: %s (%s)' % (', '.join(targets), rec_t, why))
    target = a.target or ask('Which Minecraft version?', rec_t, targets)
    if target not in targets:
        raise SystemExit('setup: %s is not supported. Choose one of: %s' % (target, ', '.join(targets)))
    if env.get('MC_TARGET') != target:
        changes['MC_TARGET'] = target
    key = mods_key(target)
    mods_dir = a.mods_dir if a.mods_dir is not None else env.get(key, '')
    if mods_dir:
        print('   mods folder: %s (%s)' % (mods_dir, 'from --mods-dir' if a.mods_dir else 'your earlier choice'))
        if not pathlib.Path(mods_dir).expanduser().is_dir():
            notes.append('%s does not exist yet. Run Minecraft %s with NeoForge once to create it.' % (mods_dir, target))
    elif not cloud:
        mods_dir = game_step(ask, a, target, notes, install_game)
    if mods_dir and env.get(key) != mods_dir:
        changes[key] = mods_dir

    print('3. Your mod\'s name')
    props = dict(re.findall(r'(?m)^(mod_id|mod_name)=(.*)$', (ROOT / 'gradle.properties').read_text(encoding='utf-8')))
    if props.get('mod_id') == 'buddymod':
        print('   It is still called "Buddy Mod". Pick a name now, or later with /name-my-mod in Claude Code.')
        name = a.name if a.name is not None else ask('Name (Enter to decide later)', '')
    else:
        print('   It is called "%s" (%s).' % (props.get('mod_name'), props.get('mod_id')))
        name = a.name or ''
    if name and not a.check:
        code, out = run([sys.executable, str(ROOT / 'tools/buddy/rename_mod.py'), name])
        print('   ' + out.replace('\n', '\n   '))
        if code != 0:
            notes.append('the mod was not renamed; try again with /name-my-mod')
        else:
            # Commit it, so the copy pushed below (and every branch made from main) has the new name.
            run(['git', 'add', '-A'])
            run(['git', '-c', 'core.hooksPath=/dev/null', 'commit', '-q', '-m', 'Name the mod: ' + name])
    repo_name = re.findall(r'(?m)^mod_id=(.*)$', (ROOT / 'gradle.properties').read_text(encoding='utf-8'))[0]

    print('4. Where your copy lives')
    r = remotes()
    if cloud:
        print('   cloud session: GitHub is managed by the session. To keep your own copy, use')
        print('   "Use this template" on GitHub and start the session on that repo.')
    elif is_upstream(r.get('origin')):
        ready, why_not = gh_ready()
        default = 'private' if ready else 'local'
        if not ready:
            print('   ' + why_not + ', so "local" is recommended for now.')
        print('   private: your own private GitHub repo (recommended). fork: a PUBLIC fork. local: no GitHub repo yet.')
        choice = a.repo or ask('private, fork or local?', default, ['private', 'fork', 'local', 'skip'])
        if choice in ('private', 'fork') and not ready:
            raise SystemExit('setup: %s needs the GitHub CLI: %s' % (choice, why_not))
        if choice == 'fork' and ask.interactive:
            if ask('A fork is PUBLIC: anyone can see what your child builds. Continue? (yes/no)', 'no',
                   ['yes', 'no']) != 'yes':
                choice = 'local'
        print('   ' + set_up_repo(choice, repo_name, a.check))
    else:
        print('   kept: origin is %s' % r.get('origin', 'not set'))

    print('5. Settings')
    if a.check:
        for k, v in changes.items():
            print('   would set %s=%s' % (k, v))
    else:
        if changes:
            write_env(changes)
            for k, v in changes.items():
                print('   %s=%s' % (k, v))
        else:
            print('   .env.local is already up to date')
        run(['git', 'config', 'core.hooksPath', '.githooks'])
        print('   git hooks: on')

    if cloud:
        print('6. Cloud environment')
        code, out = run([sys.executable, str(ROOT / 'cloud/check.py')])
        print('   ' + out.replace('\n', '\n   '))
        if code != 0:
            notes.append('the cloud environment is not ready yet; see the lines above')
        notes.append('in the cloud you build and test. To play, run ./gradlew deployToMods on your own computer.')

    print()
    for n in notes:
        print('note: ' + n)
    if cloud:
        print('Next: you are already in Claude Code. Let your child say what they want to make.')
    else:
        print('Next: type `claude` here and let your child say hi. To play what they make, open the')
        print('Minecraft launcher and pick the "Buddy Builder" profile.')
    print('Build and test by hand%s: ./gradlew build, ./tools/gate-b.sh, ./tools/client-test.sh'
          % (' (in Git Bash)' if SYS == 'Windows' else ''))
    return 0


def update_step(ask, a, cloud):
    """Merge new Buddy Builder commits into this copy. True if it did (setup then restarts)."""
    r = remotes()
    if cloud or 'upstream' not in r or is_upstream(r.get('origin')):
        return False        # the cloud manages git; no upstream; or this IS Buddy Builder
    print('0. Buddy Builder updates')
    if run(['git', 'fetch', '-q', 'upstream'])[0] != 0:
        print('   could not reach GitHub, so not checking for updates this time')
        return False
    code, out = run(['git', 'rev-list', '--count', 'HEAD..upstream/main'])
    count = int(out) if code == 0 and out.isdigit() else 0
    if not count:
        print('   up to date')
        return False
    print('   %d new: ' % count + run(['git', 'log', '--format=%s', '-1', 'upstream/main'])[1])
    later = 'ask Claude to run /update-buddy-builder'
    branch = run(['git', 'branch', '--show-current'])[1]
    if branch != 'main':
        print('   not on main (on %s), so leaving it for later: %s' % (branch or 'no branch', later))
        return False
    if run(['git', 'status', '--porcelain', '--untracked-files=no'])[1]:
        print('   this folder has unsaved changes, so leaving it for later: ' + later)
        return False
    if a.check:
        print('   would ask: bring them in?')
        return False
    if ask('Bring in the %d Buddy Builder update(s) now? (yes/no)' % count, 'yes', ['yes', 'no']) != 'yes':
        return False
    before = run(['git', 'rev-parse', 'HEAD'])[1]

    def undo(why):
        run(['git', 'merge', '--abort'])
        run(['git', 'reset', '-q', '--keep', before])
        print('   %s, so nothing changed. To update anyway: %s' % (why, later))
        return False
    if run(['git', 'merge', '-q', '--no-edit', 'upstream/main'])[0] != 0:
        return undo('your copy and the update both changed the same files')
    if OFFLINE:
        print('   skipped the build check (BUDDY_SETUP_OFFLINE)')
    else:
        print('   checking the mod still builds (the first time takes a few minutes)...')
        # Windows cannot start the ./gradlew shell script itself; gradlew.bat is the same wrapper.
        gradlew = str(ROOT / 'gradlew.bat') if SYS == 'Windows' else './gradlew'
        try:
            built = subprocess.run([gradlew, 'build', '-q', '--console=plain'], cwd=ROOT,
                                   env=dict(os.environ, PYTHON=sys.executable),
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
        except OSError as e:    # the merge is already in: undo it, never leave it half-checked
            return undo('the build could not start (%s)' % e)
        if not built:
            return undo('the mod did not build with the update')
    if 'origin' in r and run(['git', 'push', '-q', 'origin', 'HEAD:main'])[0] != 0:
        print('   updated here, but could not push to GitHub; run `git push origin main` later')
    print('   updated. Start a NEW Claude session so it picks up the new Buddy Builder mode.')
    return True


def offer(ask, a, question, notes, manual):
    """Ask before installing something. False (with a note saying how to do it by hand) if the answer
    is no, or if this is --check or a test run."""
    if a.check:
        print('   would ask: ' + question)
        return False
    if OFFLINE:
        notes.append('skipped (BUDDY_SETUP_OFFLINE): ' + manual)
        return False
    if ask(question + ' (yes/no)', 'yes', ['yes', 'no']) == 'yes':
        return True
    notes.append('to do it yourself later: ' + manual)
    return False


def tools_step(ask, a, cloud, notes, install_game):
    if SYS == 'Windows':
        refresh_path()          # installs made from another window: see them here too
    print('   %-8s ok (%s, Python %s)' % ('python', sys.executable, platform.python_version()))
    if shutil.which('git'):
        print('   %-8s ok' % 'git')
    else:
        print('   %-8s MISSING' % 'git')
        notes.append('install git: %s, then run ./setup again' % hint('git'))
    java = install_game.find_java()
    if java:
        print('   %-8s ok (Java %d)' % ('java', install_game.java_major(java)))
    elif cloud:
        print('   %-8s the cloud tools step installs it' % 'java')
    else:
        print('   %-8s MISSING: the build and the NeoForge installer need Java 21' % 'java')
        if SYS in ('Darwin', 'Windows') and offer(ask, a, 'Install Java 21 (Eclipse Temurin, about 200 MB)?', notes, hint('java')):
            try:
                java = install_game.install_java(lambda m: print('   ' + m))
                print('   java     installed')
            except Exception as e:
                notes.append('Java 21 did not install (%s). Install it by hand: %s' % (e, hint('java')))
        elif SYS not in ('Darwin', 'Windows'):
            notes.append('install Java 21: ' + hint('java'))
    if SYS == 'Windows' and java and not a.check:
        windows_java_home(java, notes)
    if shutil.which('claude') or cloud:
        print('   %-8s ok' % 'claude')
    elif SYS == 'Windows':
        print('   %-8s MISSING' % 'claude')
        if offer(ask, a, 'Install Claude Code (winget)?', notes, hint('claude')):
            if not winget_install('claude', notes):
                notes.append('Claude Code did not install. Install it by hand: ' + hint('claude'))
    elif (pathlib.Path.home() / '.local/bin/claude').exists():
        print('   %-8s installed in ~/.local/bin, but not on your PATH yet' % 'claude')
        notes.append('open a NEW terminal window so the `claude` command works (or run ~/.local/bin/claude)')
    else:
        print('   %-8s MISSING' % 'claude')
        if SYS != 'Windows' and offer(ask, a, 'Install Claude Code?', notes, CLAUDE_INSTALL):
            code = subprocess.run(['bash', '-c', CLAUDE_INSTALL]).returncode
            if code != 0 or not (shutil.which('claude') or (pathlib.Path.home() / '.local/bin/claude').exists()):
                notes.append('Claude Code did not install; see https://docs.claude.com/en/docs/claude-code/setup')
            elif not shutil.which('claude'):
                notes.append('Claude Code is installed. Open a NEW terminal window so the `claude` command works.')
    if cloud:
        return
    if not shutil.which('gh'):
        print('   %-8s MISSING (for your private copy on GitHub)' % 'gh')
        if SYS == 'Windows':
            if offer(ask, a, 'Install the GitHub CLI (winget)?', notes, hint('gh')):
                winget_install('gh', notes)
        elif shutil.which('brew') and offer(ask, a, 'Install the GitHub CLI with Homebrew?', notes, 'brew install gh'):
            subprocess.run(['brew', 'install', 'gh'])
    if shutil.which('gh'):
        if run(['gh', 'auth', 'status'])[0] == 0:
            print('   %-8s ok (signed in)' % 'gh')
        else:
            print('   %-8s not signed in to GitHub' % 'gh')
            if ask.interactive and offer(ask, a, 'Sign in to GitHub now (opens your browser)?', notes, 'gh auth login'):
                subprocess.run(['gh', 'auth', 'login', '--web', '--git-protocol', 'https'])


# ── Windows ───────────────────────────────────────────────────────────────────────────────
def refresh_path():
    """An install changes PATH in the registry, for NEW windows, not in this process. Re-read it (Machine,
    then User, as a new window would), keeping what this process already had, so a tool installed a
    moment ago, or from another window, is found now."""
    have = os.environ.get('PATH', '').split(os.pathsep)
    new = []
    try:
        import winreg
        for hive, key in ((winreg.HKEY_LOCAL_MACHINE, r'SYSTEM\CurrentControlSet\Control\Session Manager\Environment'),
                          (winreg.HKEY_CURRENT_USER, 'Environment')):
            try:
                with winreg.OpenKey(hive, key) as k:
                    new += [os.path.expandvars(x) for x in winreg.QueryValueEx(k, 'Path')[0].split(';')]
            except OSError:
                pass
    except ImportError:
        pass
    local_bin = pathlib.Path.home() / '.local' / 'bin'      # Claude Code's own installer puts it here
    if local_bin.is_dir():
        new.append(str(local_bin))
    os.environ['PATH'] = os.pathsep.join(have + [x for x in dict.fromkeys(new) if x and x not in have])


def windows_user_env(name, value, notes, why):
    """Set a user environment variable for every new window (through .NET, which also tells Explorer;
    setx would cut a long value at 1024 characters), and in this process."""
    if OFFLINE:             # a test run never changes the real user's settings
        notes.append('skipped (BUDDY_SETUP_OFFLINE): set %s=%s (%s)' % (name, value, why))
        return
    quoted = value.replace("'", "''")                      # a PowerShell single-quoted string
    code, out = run(['powershell', '-NoProfile', '-Command',
                     "[Environment]::SetEnvironmentVariable('%s', '%s', 'User')" % (name, quoted)])
    if name != 'Path':
        os.environ[name] = value
    notes.append('set %s for new windows (%s)' % (name, why) if code == 0
                 else 'could not set %s (%s): %s' % (name, why, out[:200]))


def windows_user_path_add(folder, notes, why, first=False):
    """Put a folder on the user's PATH for every new window, if it is not there yet. `first` puts it
    before the rest of the user PATH, where the Microsoft Store's python3 stub lives."""
    folder = str(folder)
    code, cur = run(['powershell', '-NoProfile', '-Command', "[Environment]::GetEnvironmentVariable('Path','User')"])
    if code != 0:
        return
    parts = [x for x in cur.strip().split(';') if x]
    if folder.lower() in [x.lower().rstrip('\\/') for x in parts]:
        return
    windows_user_env('Path', ';'.join([folder] + parts if first else parts + [folder]), notes, why)
    if folder not in os.environ.get('PATH', '').split(os.pathsep):
        os.environ['PATH'] = os.pathsep.join([folder, os.environ.get('PATH', '')] if first
                                             else [os.environ.get('PATH', ''), folder])


def winget_install(tool, notes):
    """winget, then a PATH re-read; True if the tool is found afterwards."""
    if not shutil.which('winget'):
        notes.append('winget is missing: update "App Installer" from the Microsoft Store, then run setup again')
        return False
    cmd = WINGET + [WINGET_IDS[tool]]
    print('   %-8s installing: %s' % (tool, ' '.join(cmd)), flush=True)
    try:
        subprocess.run(cmd)
    except OSError as e:
        print('   %-8s the installer did not run: %s' % (tool, e))
    refresh_path()
    found = shutil.which(tool)
    print('   %-8s %s' % (tool, 'installed' if found else 'still MISSING'))
    if found and tool == 'claude':
        # A new window must find it too (Claude Code's docs ask people to do this by hand).
        windows_user_path_add(pathlib.Path(found).parent, notes, 'so new windows find claude')
    return bool(found)


def windows_java_home(java, notes):
    """gradlew finds Java through JAVA_HOME or PATH. Point both at this JDK when neither already
    reaches Java 21 (an old JAVA_HOME, or the JDK setup itself unpacked)."""
    import install_game
    home = pathlib.Path(java).parent.parent
    cur = os.environ.get('JAVA_HOME')
    cur_ok = cur and install_game.java_major(pathlib.Path(cur) / 'bin' / 'java.exe') >= 21
    if not cur_ok:
        windows_user_env('JAVA_HOME', str(home), notes, 'Java %d, for ./gradlew' % install_game.java_major(java))
    on_path = shutil.which('java')
    if not (on_path and install_game.java_major(on_path) >= 21):
        windows_user_path_add(home / 'bin', notes, 'so new windows find Java 21', first=True)


def is_windows_admin():
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except (ImportError, AttributeError, OSError):
        return False


SHIM_MARK = "# Written by Buddy Builder's setup"


def bash_shim(name, why, command, check, notes):
    """A small script in ~/bin, which Git Bash puts first on PATH, so a command the skills, the
    allow rules and the docs use works in Git Bash. A ~/bin/<name> that setup did not write is left alone."""
    shim = pathlib.Path.home() / 'bin' / name
    body = '#!/bin/sh\n%s (tools/buddy/setup.py): %s\n%s\n' % (SHIM_MARK, why, command)
    if shim.exists():
        try:
            have = shim.read_text(encoding='utf-8')
        except (OSError, ValueError):
            have = ''
        if SHIM_MARK not in have:
            print('   %-8s %s exists and is not setup\'s: left alone' % (name, shim))
            return
        if have == body:
            print('   %-8s %s' % (name, shim))
            return
    if check:
        print('   would write %s (%s)' % (shim, why))
        return
    try:
        shim.parent.mkdir(parents=True, exist_ok=True)
        write_lf(shim, body)
        print('   %-8s wrote %s' % (name, shim))
    except OSError as e:
        notes.append('could not write %s: %s' % (shim, e))


def claude_local_settings(check, notes):
    """.claude/settings.local.json (never committed) gives Claude Code's commands on this PC: the real
    Python for ./gradlew's Python steps, UTF-8 output from the tools, and updates for a winget install
    (which does not update itself). Values already there are kept."""
    path = ROOT / '.claude' / 'settings.local.json'
    want = {'PYTHON': pathlib.Path(sys.executable).as_posix(), 'PYTHONUTF8': '1',
            'CLAUDE_CODE_PACKAGE_MANAGER_AUTO_UPDATE': '1'}
    try:
        data = json.loads(path.read_text(encoding='utf-8')) if path.is_file() else {}
    except (OSError, ValueError):
        notes.append('%s is not valid JSON, so it was left alone; add to its "env": %s' % (path, want))
        return
    env = data.setdefault('env', {})
    add = {k: v for k, v in want.items() if k not in env}
    if not add:
        print('   %-8s %s' % ('claude', 'settings.local.json: Python ok'))
        return
    if check:
        print('   would add to .claude/settings.local.json env: %s' % ', '.join(add))
        return
    env.update(add)
    write_lf(path, json.dumps(data, indent=2) + '\n')
    print('   %-8s .claude/settings.local.json: %s' % ('claude', ', '.join(add)))


def long_paths(ask, a, notes):
    """Windows' 260-character path limit. Gradle's caches run deep, and the failure (a file 'not found'
    that is there) does not say why. Java copes; git does not unless core.longpaths is on."""
    enabled = None
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'SYSTEM\CurrentControlSet\Control\FileSystem') as k:
            enabled = winreg.QueryValueEx(k, 'LongPathsEnabled')[0] == 1
    except (ImportError, OSError):
        pass
    git_long = run(['git', 'config', '--get', 'core.longpaths'])[1].strip().lower() == 'true'
    print('   %-8s Windows %s, git core.longpaths %s' % ('paths', 'on' if enabled else 'OFF' if enabled is False
                                                       else 'unknown', 'on' if git_long else 'OFF'))
    if enabled is False:
        notes.append('Windows long paths are off. Builds usually still work; if one fails with a file "not '
                     'found" that is there, turn them on (PowerShell as Administrator, once): New-ItemProperty '
                     '-Path HKLM:\\SYSTEM\\CurrentControlSet\\Control\\FileSystem -Name LongPathsEnabled -Value 1 '
                     '-PropertyType DWORD -Force')
    if not git_long and not a.check and not OFFLINE and \
            ask('Turn on long paths for git (git config --global core.longpaths true)? (yes/no)', 'yes', ['yes', 'no']) == 'yes':
        run(['git', 'config', '--global', 'core.longpaths', 'true'])


def windows_step(ask, a, notes):
    """What Windows needs beyond the tools: a python3 for Git Bash, Claude Code's settings, long paths."""
    if is_windows_admin():
        print('   %-8s this window is running as Administrator' % 'admin')
        notes.append('this window runs as Administrator: what setup installs for you lands where your '
                     'everyday windows may not look. Next time, open PowerShell with a plain click.')
    # The skills, the allow rules and the docs say `python3`; Windows Python has no python3 command
    # (only a Store stub). The shim also makes Python print UTF-8 with LF (tools/winpy).
    exe = pathlib.Path(sys.executable).as_posix()
    winpy = (ROOT / 'tools' / 'winpy').as_posix()
    bash_shim('python3', 'Windows Python has no python3 command',
              'export PYTHONUTF8=1\nexport PYTHONPATH="%s${PYTHONPATH:+;$PYTHONPATH}"\nexec "%s" "$@"' % (winpy, exe),
              a.check, notes)
    unzip = shutil.which('unzip')
    if not unzip or (os.path.getsize(unzip) < 4096 and SHIM_MARK in pathlib.Path(unzip).read_text(encoding='utf-8', errors='replace')):
        bash_shim('unzip', 'Git for Windows has no unzip; tools/buddy/zipls.py takes its -l/-p/-Z1 flags',
                  'exec "%s" "%s" "$@"' % (exe, (ROOT / 'tools' / 'buddy' / 'zipls.py').as_posix()), a.check, notes)
    if not a.check:
        # Git Bash puts ~/bin first only in a login shell; on the user PATH every bash finds the shims.
        windows_user_path_add(pathlib.Path.home() / 'bin', notes, 'so Git Bash finds python3', first=True)
    claude_local_settings(a.check, notes)
    long_paths(ask, a, notes)


def game_step(ask, a, target, notes, install_game):
    """Get Minecraft ready to play this version. Returns the mods folder, or '' if it isn't ready."""
    missing = install_game.status(target)
    mods = str(install_game.game_dir(target) / 'mods')
    if not missing:
        print('   ready to play: the "%s" profile in the Minecraft launcher' % install_game.profile_name(target))
        return mods
    print('   to play the mod, this needs: ' + ', '.join(missing))
    question = ('Set up Minecraft %s for playing: NeoForge, plus a "%s" profile in the launcher '
                'with its own worlds?' % (target, install_game.profile_name(target)))
    if not offer(ask, a, question, notes, 'run ./setup again'):
        return ''

    def wait_for_launcher():
        if not ask.interactive:
            return False
        input('   The Minecraft launcher is open. Quit it (%s), then press Enter: '
              % ('close its window, and check the taskbar\'s hidden icons' if SYS == 'Windows' else 'Cmd+Q'))
        return True
    try:
        install_game.ensure(target, say=lambda m: print('   ' + m), wait_for_launcher=wait_for_launcher)
    except Exception as e:
        notes.append(str(e))
        return ''
    print('   ready to play: open the Minecraft launcher and pick "%s"' % install_game.profile_name(target))
    return mods


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (KeyboardInterrupt, EOFError):
        print('\nsetup: stopped. Nothing after the last line shown was changed.')
        sys.exit(130)
