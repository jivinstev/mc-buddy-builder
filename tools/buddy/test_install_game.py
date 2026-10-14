#!/usr/bin/env python3
"""tools/buddy/install_game.py against a fake home folder, with no network and no real installer.

    python3 tools/buddy/test_install_game.py

The real thing (Adoptium's Java, NeoForge's installer) was run by hand into a throwaway home; this
pins the logic around it: the profile it writes, the profiles it puts back, the checksum, the
launcher being open, and that a second run does nothing."""
import hashlib, io, json, os, pathlib, sys, tempfile, zipfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import install_game as g
REAL_LAUNCHER_RUNNING = g.launcher_running

JAR = b'fake installer'


def main():
    fails = []

    def check(name, ok):
        print('  %-56s %s' % (name, 'ok' if ok else 'FAIL'))
        if not ok:
            fails.append(name)

    with tempfile.TemporaryDirectory() as t:
        home = pathlib.Path(t)
        # launcher_dir() reads %APPDATA% on Windows: point it into the temp folder too, or this test
        # would edit the REAL launcher_profiles.json there.
        os.environ['APPDATA'] = str(home / 'AppData/Roaming')
        os.environ['LOCALAPPDATA'] = str(home / 'AppData/Local')
        calls = {'installer': 0, 'sha': hashlib.sha256(JAR).hexdigest(), 'open': False}
        g.home = lambda: home
        g.find_java = lambda minimum=21: pathlib.Path('/fake/java')
        g.launcher_running = lambda: calls['open']

        def fake_get(url, dest=None):
            if url.endswith('.sha256'):
                return calls['sha'].encode()
            pathlib.Path(dest).write_bytes(JAR)

        def fake_run(cmd, **kw):
            calls['installer'] += 1
            assert '--install-client' in cmd, cmd
            mc = pathlib.Path(cmd[cmd.index('--install-client') + 1])
            (mc / 'versions' / ('neoforge-' + g.neo_version('26.2'))).mkdir(parents=True)
            lp = mc / 'launcher_profiles.json'
            d = json.loads(lp.read_text(encoding='utf-8'))
            d['profiles']['NeoForge'] = {'name': 'NeoForge', 'lastVersionId': 'neoforge-x'}   # added
            d['profiles']['mine']['lastVersionId'] = 'neoforge-x'                              # repointed
            lp.write_text(json.dumps(d), encoding='utf-8')
            return type('R', (), {'returncode': 0, 'stdout': '', 'stderr': ''})()
        g.get, g.run = fake_get, fake_run
        say = lambda m: None

        try:
            g.ensure('26.2', say=say)
            check('no launcher_profiles.json: refuses, says open the launcher', False)
        except RuntimeError as e:
            check('no launcher_profiles.json: refuses, says open the launcher', 'open the launcher' in str(e))

        lp = g.launcher_dir() / 'launcher_profiles.json'
        lp.parent.mkdir(parents=True)
        lp.write_text(json.dumps({'profiles': {'mine': {'name': 'Mine', 'lastVersionId': 'latest-release'}}}), encoding='utf-8')
        original = json.loads(lp.read_text(encoding='utf-8'))['profiles']

        calls['open'] = True
        try:
            g.ensure('26.2', say=say)
            check('launcher open: refuses without touching anything', False)
        except RuntimeError as e:
            check('launcher open: refuses without touching anything',
                  'quit the Minecraft launcher' in str(e) and calls['installer'] == 0)
        waits = []
        g.ensure('26.2', say=say, wait_for_launcher=lambda: waits.append(1) or calls.update(open=False) or True)
        check('launcher open: waits for the grown-up to quit it, then goes on', waits == [1] and calls['installer'] == 1)

        profiles = json.loads(lp.read_text(encoding='utf-8'))['profiles']
        mine = profiles.get(g.profile_key('26.2'), {})
        check('adds the Buddy Builder profile', mine.get('name') == 'Buddy Builder (26.2)'
              and mine.get('lastVersionId') == 'neoforge-' + g.neo_version('26.2'))
        check('the profile has its own game folder', mine.get('gameDir') == str(g.game_dir('26.2'))
              and g.game_dir('26.2').name.endswith('minecraft-26.2'))
        check('the mods folder exists', (g.game_dir('26.2') / 'mods').is_dir())
        check('puts back the profile the installer repointed', profiles.get('mine') == original['mine'])
        check('removes the profile the installer added', 'NeoForge' not in profiles)
        check('backs up launcher_profiles.json first',
              json.loads(lp.with_name('launcher_profiles.json.buddy-builder.bak').read_text(encoding='utf-8'))['profiles'] == original)
        check('status: nothing missing', g.status('26.2') == [])

        calls['open'] = True
        g.ensure('26.2', say=say)
        check('a second run does nothing (not even wait for the launcher)', calls['installer'] == 1)
        calls['open'] = False

        calls['sha'] = '0' * 64
        try:
            g.ensure('1.21.1', say=say)
            check('a damaged download is refused before it runs', False)
        except RuntimeError as e:
            check('a damaged download is refused before it runs', 'checksum' in str(e) and calls['installer'] == 1)
        calls['sha'] = hashlib.sha256(JAR).hexdigest()

        # The Microsoft Store / Xbox app launcher keeps launcher_profiles_microsoft_store.json. With
        # both files there, both get the profile; with only the Store one, that one does.
        store = lp.with_name('launcher_profiles_microsoft_store.json')
        store.write_text(json.dumps({'profiles': {'xbox': {'name': 'Xbox'}}}), encoding='utf-8')
        check('status: the Store launcher\'s file lacks the profile', g.status('26.2') != [])
        g.ensure('26.2', say=say)
        sp = json.loads(store.read_text(encoding='utf-8'))['profiles']
        check('the Store launcher\'s file gets the profile too', g.profile_key('26.2') in sp and 'xbox' in sp)
        check('status: nothing missing with both files', g.status('26.2') == [])
        lp.unlink()
        check('only the Store launcher\'s file: the launcher counts as set up', g.status('26.2') == [])

    # Windows: Java from Adoptium's zip into %LOCALAPPDATA%, checksum-checked, no installer.
    with tempfile.TemporaryDirectory() as t:
        os.environ['LOCALAPPDATA'] = t
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as zf:
            zf.writestr('jdk-21.0.9+10/bin/java.exe', b'MZ')
            zf.writestr('jdk-21.0.9+10/release', 'JAVA_VERSION="21.0.9"\n')
        blob = buf.getvalue()
        meta = json.dumps([{'binary': {'package': {'name': 'jdk.zip', 'size': len(blob), 'link': 'https://x/jdk.zip',
                                                   'checksum': hashlib.sha256(blob).hexdigest()}}}]).encode()
        asked = []

        def zip_get(url, dest=None):
            asked.append(url)
            if dest is None:
                return meta
            pathlib.Path(dest).write_bytes(blob)
        g.get = zip_get
        java = g.install_java_windows(say)
        check('Windows Java: unpacked into %LOCALAPPDATA%\\BuddyBuilder\\jdk-21',
              java == pathlib.Path(t) / 'BuddyBuilder/jdk-21/bin/java.exe' and java.is_file())
        check('Windows Java: asks Adoptium for the Windows build', 'os=windows' in asked[0])
        g.install_java_windows(say)
        check('Windows Java: a second install replaces the first', (pathlib.Path(t) / 'BuddyBuilder/jdk-21/release').is_file())
        blob = b'damaged'
        try:
            g.install_java_windows(say)
            check('Windows Java: a damaged download is refused', False)
        except RuntimeError as e:
            check('Windows Java: a damaged download is refused', 'checksum' in str(e))

    # Windows: the open launcher is found by its process name (tasklist's CSV).
    sys_was, run_was = g.SYS, g.run
    g.SYS = 'Windows'
    for listing, want in (('"Minecraft.exe","1","Console","1","200 K"', True),
                          ('"MinecraftLauncher.exe","1","Console","1","200 K"', True),
                          ('"Minecraft.Windows.exe","1","Console","1","200 K"\n"java.exe","2","Console","1","9 K"', False)):
        g.run = lambda cmd, **kw: type('R', (), {'returncode': 0, 'stdout': listing, 'stderr': ''})()
        check('Windows launcher open? %s' % listing.split(',')[0], REAL_LAUNCHER_RUNNING() == want)
    g.SYS, g.run = sys_was, run_was

    print('test_install_game: %s' % ('PASS' if not fails else 'FAIL (%d)' % len(fails)))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
