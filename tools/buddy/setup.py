#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""First-run setup for a Buddy Builder mod. Usually run as `./setup`.

    ./setup                  asks each question with a recommendation; Enter accepts it
    ./setup --yes            take every recommendation (re-run: keep every earlier answer)
    ./setup --check          change nothing; say what setup would do
    ./setup --target 1.21.1 --mods-dir ~/path/mods --name "Dragon Treasure" --repo private

WHAT IT DOES
    1. Checks the tools: git, Java 21, Python, Claude Code, and the GitHub CLI (optional).
    2. Finds the Minecraft installs on this machine and recommends one. If an install already
       runs NeoForge on a version this mod supports, that version and its mods folder are the
       recommendation. Otherwise the recommendation is the newest supported version.
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

HINTS = {
    'git': {'Darwin': 'xcode-select --install', 'Windows': 'winget install --id Git.Git',
            'Linux': 'sudo apt install git'},
    'java': {'Darwin': 'brew install --cask temurin@21', 'Windows': 'winget install --id EclipseAdoptium.Temurin.21.JDK',
             'Linux': 'sudo apt install openjdk-21-jdk'},
    'claude': {'Darwin': 'https://docs.claude.com/en/docs/claude-code/setup',
               'Windows': 'https://docs.claude.com/en/docs/claude-code/setup',
               'Linux': 'https://docs.claude.com/en/docs/claude-code/setup'},
    'gh': {'Darwin': 'brew install gh', 'Windows': 'winget install --id GitHub.cli',
           'Linux': 'https://cli.github.com'},
}


def hint(tool):
    return HINTS[tool].get(SYS, HINTS[tool]['Linux'])


def run(cmd, cwd=ROOT, check=False):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if check and p.returncode != 0:
        raise SystemExit('setup: `%s` failed:\n%s' % (' '.join(cmd), p.stdout + p.stderr))
    return p.returncode, (p.stdout + p.stderr).strip()


# ── .env.local ────────────────────────────────────────────────────────────────────────────
def read_env():
    out = {}
    if ENV.is_file():
        for line in ENV.read_text().splitlines():
            m = re.match(r'\s*([A-Za-z_][A-Za-z0-9_]*)\s*=(.*)$', line)
            if m and not line.lstrip().startswith('#'):
                out[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    return out


def write_env(changes):
    lines = ENV.read_text().splitlines() if ENV.is_file() else [
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
    ENV.write_text('\n'.join(out) + '\n')


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
    notes, changes = [], {}

    print('1. Tools')
    for tool in ('git', 'java', 'python3', 'claude', 'gh'):
        ok = shutil.which(tool) is not None
        extra = ''
        if tool == 'java' and ok:
            _, out = run(['java', '-version'])
            m = re.search(r'version "(\d+)', out)
            major = int(m.group(1)) if m else 0
            extra = ' (Java %s)' % (major or '?')
            if major and major < 21:
                ok = False
                extra += ' - need 21 or newer'
        print('   %-8s %s%s' % (tool, 'ok' if ok else 'MISSING', extra))
        if not ok and tool in HINTS:
            (notes if tool == 'gh' else notes).append('install %s: %s' % (tool, hint(tool)))
    print('   (Minecraft 26.2 also needs Java 25; the build downloads it by itself.)')

    print('2. Minecraft')
    targets = supported_targets()
    installs = find_installs()
    for inst in installs:
        mods = 'no mods folder' if inst.get('mods') is None else '%d mods' % inst['mods']
        print('   found %s: %s (%s; %s)' % (inst['kind'], inst['path'],
                                          ', '.join(inst.get('loaders') or inst.get('versions') or ['?']), mods))
    if not installs:
        print('   no Minecraft install found here. That is fine for building and testing.')
    rec_t, rec_dir, why = recommend(installs, targets)
    if env.get('MC_TARGET') in targets:
        rec_t, why = env['MC_TARGET'], 'your earlier choice'
    print('   supported versions: %s. Recommended: %s (%s)' % (', '.join(targets), rec_t, why))
    target = a.target or ask('Which Minecraft version?', rec_t, targets)
    if target not in targets:
        raise SystemExit('setup: %s is not supported. Choose one of: %s' % (target, ', '.join(targets)))
    if env.get('MC_TARGET') != target:
        changes['MC_TARGET'] = target
    key = mods_key(target)
    if env.get(key):
        rec_dir = env[key]
    if rec_dir and neoforge_target_of_dir(installs, rec_dir) not in (None, target):
        rec_dir = ''
    mods_dir = a.mods_dir if a.mods_dir is not None else ask(
        'Mods folder of the Minecraft %s install you play (type none to skip)' % target, rec_dir)
    if mods_dir and env.get(key) != mods_dir:
        changes[key] = mods_dir
    if mods_dir and not pathlib.Path(mods_dir).expanduser().is_dir():
        notes.append('%s does not exist yet. Run Minecraft %s with NeoForge once to create it.' % (mods_dir, target))

    print('3. Your mod\'s name')
    props = dict(re.findall(r'(?m)^(mod_id|mod_name)=(.*)$', (ROOT / 'gradle.properties').read_text()))
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
    repo_name = re.findall(r'(?m)^mod_id=(.*)$', (ROOT / 'gradle.properties').read_text())[0]

    print('4. Where your copy lives')
    r = remotes()
    if is_upstream(r.get('origin')):
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

    print()
    for n in notes:
        print('note: ' + n)
    print('Next: open this folder in Claude Code (`claude`) and let your child say hi.')
    print('Build and test by hand: ./gradlew build, ./tools/gate-b.sh, ./tools/client-test.sh')
    return 0


def neoforge_target_of_dir(installs, mods_dir):
    """The NeoForge version of the install a mods folder belongs to, if setup found it."""
    want = os.path.realpath(os.path.expanduser(str(pathlib.Path(mods_dir).parent)))
    for inst in installs:
        if os.path.realpath(inst['path']) == want:
            for loader in inst.get('loaders', []):
                t = neoforge_target(loader)
                if t:
                    return t
    return None


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (KeyboardInterrupt, EOFError):
        print('\nsetup: stopped. Nothing after the last line shown was changed.')
        sys.exit(130)
