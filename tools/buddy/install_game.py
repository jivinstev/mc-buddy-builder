#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Gets this computer ready to PLAY the mod: Java 21, NeoForge, and a "Buddy Builder" profile in the
official Minecraft launcher with its own game folder. Used by tools/buddy/setup.py.

    python3 tools/buddy/install_game.py --target 26.2 --check   # say what is missing; change nothing
    python3 tools/buddy/install_game.py --target 26.2           # install it

WHAT IT DOES
    1. Java 21 or newer, for the build (Gradle) and for running the NeoForge installer. If there is
       none, on a Mac it downloads Eclipse Temurin 21 from Adoptium into
       ~/Library/Java/JavaVirtualMachines: no password, and the Mac's own `java` command finds it.
    2. NeoForge, the exact version this mod builds against (versions/<target>.properties), installed
       with NeoForge's own installer (`--install-client`) into the official launcher's folder.
    3. A launcher profile called "Buddy Builder (<target>)" that plays that NeoForge with its own game
       folder (minecraft-<target>, next to the launcher's folder), so the family's normal worlds and
       mods are never touched. Its mods/ folder is where `./gradlew deployToMods` puts the mod.

    The launcher must have been opened once (it creates launcher_profiles.json), and must be closed
    while the profile is written, or it overwrites the file when it quits. launcher_profiles.json is
    backed up first, and a "NeoForge" profile the installer adds or repoints is put back as it was.
    Running it again does only what is still missing.

Standard library only.
"""
import argparse, datetime, hashlib, json, os, pathlib, platform, re, shutil, subprocess, sys, tarfile
import tempfile, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
SYS = platform.system()
NEO_MAVEN = 'https://maven.neoforged.net/releases/net/neoforged/neoforge'
ADOPTIUM = 'https://api.adoptium.net/v3/assets/latest/21/hotspot?os=mac&architecture=%s&image_type=jdk'
PROFILE_ICON = 'Crafting_Table'


# ── seams the tests replace ───────────────────────────────────────────────────────────────
def home():
    return pathlib.Path.home()


def get(url, dest=None):
    """The body of url, or (with dest) stream it to dest."""
    req = urllib.request.Request(url, headers={'User-Agent': 'mc-buddy-builder-setup'})
    with urllib.request.urlopen(req, timeout=60) as r:
        if dest is None:
            return r.read()
        with open(dest, 'wb') as f:
            shutil.copyfileobj(r, f, 1 << 20)


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def launcher_running():
    """True if this user's official Minecraft launcher is open."""
    if SYS != 'Darwin':
        return False
    p = run(['ps', '-axo', 'uid=,comm='])
    me = str(os.getuid())
    return any(line.split(None, 1)[0] == me and 'Minecraft.app/Contents/MacOS/launcher' in line
               for line in p.stdout.splitlines() if line.strip())


# ── where things are ──────────────────────────────────────────────────────────────────────
def launcher_dir():
    if SYS == 'Darwin':
        return home() / 'Library/Application Support/minecraft'
    if SYS == 'Windows':
        return pathlib.Path(os.environ.get('APPDATA', home() / 'AppData/Roaming')) / '.minecraft'
    return home() / '.minecraft'


def game_dir(target):
    """The profile's own game folder: minecraft-26.2 next to the launcher's minecraft folder (the
    layout tools/buddy/find_minecraft.py already recognises)."""
    d = launcher_dir()
    return d.parent / ('%s-%s' % (d.name, target))


def neo_version(target):
    props = (ROOT / 'versions' / ('%s.properties' % target)).read_text(encoding='utf-8')
    return re.search(r'(?m)^neo_version=(.+)$', props).group(1).strip()


def profile_key(target):
    return 'buddy-builder-' + target


def profile_name(target):
    return 'Buddy Builder (%s)' % target


# ── Java ──────────────────────────────────────────────────────────────────────────────────
def java_major(java):
    try:
        p = run([str(java), '-version'], timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return 0
    m = re.search(r'version "(\d+)(?:\.(\d+))?', p.stdout + p.stderr)
    if not m:
        return 0
    major = int(m.group(1))
    return int(m.group(2) or 0) if major == 1 else major


def find_java(minimum=21):
    """A java that really runs (a Mac's /usr/bin/java is only a stub when no JDK is installed)."""
    cands = []
    if os.environ.get('JAVA_HOME'):
        cands.append(pathlib.Path(os.environ['JAVA_HOME']) / 'bin/java')
    if shutil.which('java'):
        cands.append(pathlib.Path(shutil.which('java')))
    for jvms in (home() / 'Library/Java/JavaVirtualMachines', pathlib.Path('/Library/Java/JavaVirtualMachines')):
        if jvms.is_dir():
            cands += sorted(jvms.glob('*/Contents/Home/bin/java'), reverse=True)
    for c in cands:
        if c.exists() and java_major(c) >= minimum:
            return c
    return None


def install_java(say):
    """Temurin 21 into ~/Library/Java/JavaVirtualMachines (a Mac only). Returns its java."""
    if SYS != 'Darwin':
        raise RuntimeError('installing Java by itself only works on a Mac so far')
    arch = 'aarch64' if platform.machine() == 'arm64' else 'x64'
    pkg = json.loads(get(ADOPTIUM % arch))[0]['binary']['package']
    say('downloading %s (%d MB) from Adoptium' % (pkg['name'], pkg['size'] // 1_000_000))
    dest = home() / 'Library/Java/JavaVirtualMachines/temurin-21.jdk'
    with tempfile.TemporaryDirectory() as t:
        tgz = pathlib.Path(t) / pkg['name']
        get(pkg['link'], tgz)
        if hashlib.sha256(tgz.read_bytes()).hexdigest() != pkg['checksum']:
            raise RuntimeError('the Java download was damaged (checksum mismatch); run ./setup again')
        with tarfile.open(tgz) as tf:
            tf.extractall(t, filter='data') if hasattr(tarfile, 'data_filter') else tf.extractall(t)
        top = next(p for p in pathlib.Path(t).iterdir() if p.is_dir() and (p / 'Contents/Home/bin/java').exists())
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            shutil.rmtree(dest)
        shutil.move(str(top), str(dest))
    return dest / 'Contents/Home/bin/java'


# ── NeoForge and the profile ──────────────────────────────────────────────────────────────
def neoforge_installed(target):
    return (launcher_dir() / 'versions' / ('neoforge-' + neo_version(target))).is_dir()


def profile_ok(target):
    try:
        prof = json.loads((launcher_dir() / 'launcher_profiles.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return False
    p = prof.get('profiles', {}).get(profile_key(target), {})
    return (p.get('lastVersionId') == 'neoforge-' + neo_version(target)
            and p.get('gameDir') == str(game_dir(target)))


def install_neoforge(target, java, say):
    v = neo_version(target)
    url = '%s/%s/neoforge-%s-installer.jar' % (NEO_MAVEN, v, v)
    with tempfile.TemporaryDirectory() as t:
        jar = pathlib.Path(t) / 'installer.jar'
        say('downloading the NeoForge %s installer' % v)
        get(url, jar)
        want = get(url + '.sha256').decode().split()[0].strip().lower()
        if hashlib.sha256(jar.read_bytes()).hexdigest() != want:
            raise RuntimeError('the NeoForge download was damaged (checksum mismatch); run ./setup again')
        say('installing NeoForge %s into Minecraft (a minute or two: it downloads Minecraft %s too)' % (v, target))
        r = run([str(java), '-jar', str(jar), '--install-client', str(launcher_dir())], cwd=t)
    if r.returncode != 0 or not neoforge_installed(target):
        tail = '\n'.join((r.stdout + r.stderr).strip().splitlines()[-15:])
        raise RuntimeError('the NeoForge installer did not finish:\n' + tail)


def write_profile(target, before):
    """Add our profile, and put back any profile the NeoForge installer added or changed."""
    path = launcher_dir() / 'launcher_profiles.json'
    data = json.loads(path.read_text(encoding='utf-8'))
    profiles = data.setdefault('profiles', {})
    for key in list(profiles):
        if key not in before:
            if key != profile_key(target):
                del profiles[key]
        elif profiles[key] != before[key]:
            profiles[key] = before[key]
    now = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z')
    mine = dict(profiles.get(profile_key(target), {}))
    mine.update({'name': profile_name(target), 'type': 'custom', 'icon': PROFILE_ICON,
                 'lastVersionId': 'neoforge-' + neo_version(target), 'gameDir': str(game_dir(target))})
    mine.setdefault('created', now)
    mine['lastUsed'] = now          # the launcher lists the most recently used profile first
    profiles[profile_key(target)] = mine
    path.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')


# ── the whole thing ───────────────────────────────────────────────────────────────────────
def status(target):
    """What is still missing, as short phrases. Empty when ready to play."""
    missing = []
    if not find_java():
        missing.append('Java 21')
    if not (launcher_dir() / 'launcher_profiles.json').is_file():
        missing.append('the Minecraft launcher (or it has never been opened)')
        return missing
    if not neoforge_installed(target):
        missing.append('NeoForge %s' % neo_version(target))
    if not profile_ok(target):
        missing.append('the "%s" launcher profile' % profile_name(target))
    if not (game_dir(target) / 'mods').is_dir():
        missing.append('its mods folder')
    return missing


def ensure(target, say=print, wait_for_launcher=None):
    """Install whatever is missing. Returns the mods folder. Raises RuntimeError with a message for
    the grown-up when it can't."""
    java = find_java()
    if not java:
        java = install_java(say)
        say('Java 21: installed')
    lp = launcher_dir() / 'launcher_profiles.json'
    if not lp.is_file():
        raise RuntimeError('Minecraft: Java Edition isn\'t set up on this Mac account yet. Install it from '
                           'minecraft.net, open the launcher once and sign in, quit it, then run ./setup again.')
    if not (neoforge_installed(target) and profile_ok(target)):
        while launcher_running():
            if wait_for_launcher is None or not wait_for_launcher():
                raise RuntimeError('quit the Minecraft launcher, then run ./setup again (it rewrites the '
                                   'launcher\'s profiles when it quits, which would undo this step)')
        shutil.copy2(lp, lp.with_name('launcher_profiles.json.buddy-builder.bak'))
        before = json.loads(lp.read_text(encoding='utf-8')).get('profiles', {})
        if not neoforge_installed(target):
            install_neoforge(target, java, say)
        write_profile(target, before)
        say('launcher profile "%s": ready' % profile_name(target))
    mods = game_dir(target) / 'mods'
    mods.mkdir(parents=True, exist_ok=True)
    return mods


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--target', required=True)
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    if a.check:
        missing = status(a.target)
        print('ready to play' if not missing else 'missing: ' + ', '.join(missing))
        return 0
    try:
        print('mods folder: %s' % ensure(a.target))
    except RuntimeError as e:
        print('install_game: ' + str(e))
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
