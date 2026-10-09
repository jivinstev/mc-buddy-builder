#!/usr/bin/env python3
"""tools/buddy/install_game.py against a fake home folder, with no network and no real installer.

    python3 tools/buddy/test_install_game.py

The real thing (Adoptium's Java, NeoForge's installer) was run by hand into a throwaway home; this
pins the logic around it: the profile it writes, the profiles it puts back, the checksum, the
launcher being open, and that a second run does nothing."""
import hashlib, json, pathlib, sys, tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import install_game as g

JAR = b'fake installer'


def main():
    fails = []

    def check(name, ok):
        print('  %-56s %s' % (name, 'ok' if ok else 'FAIL'))
        if not ok:
            fails.append(name)

    with tempfile.TemporaryDirectory() as t:
        home = pathlib.Path(t)
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
            d = json.loads(lp.read_text())
            d['profiles']['NeoForge'] = {'name': 'NeoForge', 'lastVersionId': 'neoforge-x'}   # added
            d['profiles']['mine']['lastVersionId'] = 'neoforge-x'                              # repointed
            lp.write_text(json.dumps(d))
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
        lp.write_text(json.dumps({'profiles': {'mine': {'name': 'Mine', 'lastVersionId': 'latest-release'}}}))
        original = json.loads(lp.read_text())['profiles']

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

        profiles = json.loads(lp.read_text())['profiles']
        mine = profiles.get(g.profile_key('26.2'), {})
        check('adds the Buddy Builder profile', mine.get('name') == 'Buddy Builder (26.2)'
              and mine.get('lastVersionId') == 'neoforge-' + g.neo_version('26.2'))
        check('the profile has its own game folder', mine.get('gameDir') == str(g.game_dir('26.2'))
              and g.game_dir('26.2').name.endswith('minecraft-26.2'))
        check('the mods folder exists', (g.game_dir('26.2') / 'mods').is_dir())
        check('puts back the profile the installer repointed', profiles.get('mine') == original['mine'])
        check('removes the profile the installer added', 'NeoForge' not in profiles)
        check('backs up launcher_profiles.json first',
              json.loads(lp.with_name('launcher_profiles.json.buddy-builder.bak').read_text())['profiles'] == original)
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

    print('test_install_game: %s' % ('PASS' if not fails else 'FAIL (%d)' % len(fails)))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
