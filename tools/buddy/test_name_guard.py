#!/usr/bin/env python3
"""The naming guard (.claude/hooks/name_guard.py) refuses edits to the mod until it is named.

    python3 tools/buddy/test_name_guard.py

Runs the hook as Claude Code does (JSON on stdin) against throwaway project folders."""
import json, os, pathlib, subprocess, sys, tempfile

HOOK = pathlib.Path(__file__).resolve().parents[2] / '.claude/hooks/name_guard.py'


def run(root, path, mod_id='buddymod', env_local=None, extra_env=None, tool='Edit'):
    (root / 'gradle.properties').write_text('mod_id=%s\nmod_name=X\n' % mod_id)
    envf = root / '.env.local'
    envf.unlink(missing_ok=True)
    if env_local is not None:
        envf.write_text(env_local)
    env = {k: v for k, v in os.environ.items() if k != 'BUDDY_MAINTAINER'}
    env['CLAUDE_PROJECT_DIR'] = str(root)
    env.update(extra_env or {})
    key = 'notebook_path' if tool == 'NotebookEdit' else 'file_path'
    p = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(
        {'tool_name': tool, 'tool_input': {key: path}, 'cwd': str(root)}),
        capture_output=True, text=True, env=env)
    return p.returncode, p.stderr


def main():
    fails = []
    with tempfile.TemporaryDirectory() as d:
        root = pathlib.Path(d)
        java = str(root / 'src/main/java/com/buddymod/Dragon.java')
        cases = [
            ('unnamed: a mod file is refused', dict(path=java), 2),
            ('unnamed: a relative path is refused too', dict(path='art/dragon.txt'), 2),
            ('unnamed: a NotebookEdit is refused', dict(path=java, tool='NotebookEdit'), 2),
            ('unnamed: a doc is fine', dict(path=str(root / 'docs/notes.md')), 0),
            ('unnamed: a look-alike folder is fine', dict(path=str(root / 'srcs/x.java')), 0),
            ('unnamed: escaping with .. is still caught', dict(path=str(root / 'docs/../src/x.java')), 2),
            ('named: the mod file is fine', dict(path=java, mod_id='dragontreasure'), 0),
            ('kept the starter name on purpose', dict(path=java, env_local='MC_TARGET=26.2\nKEEP_STARTER_NAME=yes\n'), 0),
            ('a different .env.local does not unlock it', dict(path=java, env_local='MC_TARGET=26.2\n'), 2),
            ('maintainer', dict(path=java, extra_env={'BUDDY_MAINTAINER': '1'}), 0),
        ]
        for name, kw, want in cases:
            code, err = run(root, **kw)
            ok = code == want and (want == 0 or '/name-my-mod' in err)
            print('  %-48s %s' % (name, 'ok' if ok else 'FAIL (exit %d)' % code))
            if not ok:
                fails.append(name)
        # A broken input must allow, never stop a session cold.
        p = subprocess.run([sys.executable, str(HOOK)], input='not json', capture_output=True, text=True)
        if p.returncode != 0:
            fails.append('bad input did not allow')
        print('  %-48s %s' % ('bad input allows', 'ok' if p.returncode == 0 else 'FAIL'))
    print('test_name_guard: %s' % ('PASS' if not fails else 'FAIL (%d)' % len(fails)))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
