#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Give the starter mod its own name.

    python3 tools/buddy/rename_mod.py "Dragon Treasure"          # does it
    python3 tools/buddy/rename_mod.py "Dragon Treasure" --dry-run

From the display name it derives:
    mod id      dragontreasure        (lowercase letters and digits; what Minecraft uses inside)
    package     com.dragontreasure    (the Java folder)
    main class  DragonTreasureMod

and rewrites every place the old ones appear: gradle.properties, settings.gradle, the Java
package folders in src/main, src/test, src/mc21 and src/mc26, the asset and data folders,
and every `oldid:` reference and lang key inside them. Docs and tools are left alone.

It reads the CURRENT names from gradle.properties, so renaming twice works.
Exit 0 renamed (or would rename), 2 bad name or nothing to do.
"""
import argparse, os, re, shutil, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SOURCE_ROOTS = ['src/main/java', 'src/test/java', 'src/mc21/java', 'src/mc26/java']
RESOURCE_ROOTS = ['src/main/resources', 'src/mc21/resources', 'src/mc26/resources']
TEXT_EXT = ('.java', '.json', '.toml', '.mcmeta', '.properties', '.txt', '.md')
# Java keywords and names Minecraft/NeoForge already use for themselves.
RESERVED = {'minecraft', 'neoforge', 'forge', 'java', 'mod', 'test', 'abstract', 'class',
            'default', 'package', 'import', 'new', 'public', 'static', 'void', 'int', 'true',
            'false', 'null', 'this', 'super', 'enum', 'record', 'final', 'interface'}


def derive(display):
    words = re.findall(r'[A-Za-z0-9]+', display)
    if not words:
        raise ValueError('the name needs at least one letter')
    modid = ''.join(w.lower() for w in words)
    if not modid[0].isalpha():
        raise ValueError('the name must start with a letter')
    if len(modid) < 3 or len(modid) > 40:
        raise ValueError('the name must make an id of 3 to 40 letters and digits (got %r)' % modid)
    if modid in RESERVED:
        raise ValueError('%r is a name Minecraft or Java already uses' % modid)
    cls = ''.join(w[0].upper() + w[1:] for w in words)
    if not cls.endswith('Mod'):
        cls += 'Mod'
    return modid, 'com.' + modid, cls


def read_props(path):
    props = {}
    for line in open(path, encoding='utf-8'):
        m = re.match(r'\s*([\w.]+)\s*=(.*)$', line)
        if m:
            props[m.group(1)] = m.group(2).strip()
    return props


def main_class(old_pkg):
    d = os.path.join(ROOT, 'src/main/java', *old_pkg.split('.'))
    for fn in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        if fn.endswith('.java') and '@Mod(' in open(os.path.join(d, fn), encoding='utf-8').read():
            return fn[:-5]
    raise SystemExit('could not find the @Mod class under %s' % d)


def plan(display):
    props = read_props(os.path.join(ROOT, 'gradle.properties'))
    old_id, old_pkg, old_name = props['mod_id'], props['mod_group_id'], props['mod_name']
    new_id, new_pkg, new_cls = derive(display)
    old_cls = main_class(old_pkg)
    if (old_id, old_name) == (new_id, display):
        raise SystemExit('the mod is already called %r (%s)' % (display, new_id))
    return dict(old_id=old_id, old_pkg=old_pkg, old_name=old_name, old_cls=old_cls,
                new_id=new_id, new_pkg=new_pkg, new_name=display, new_cls=new_cls)


def rewrite_text(s, p):
    s = s.replace(p['old_pkg'] + '.', p['new_pkg'] + '.').replace(p['old_pkg'] + ';', p['new_pkg'] + ';')
    s = re.sub(r'\b%s\b' % re.escape(p['old_cls']), p['new_cls'], s)
    # ids: "oldid:thing", "assets/oldid", "itemGroup.oldid", "block.oldid.x", MODID = "oldid"
    s = re.sub(r'(?<!\w)%s(?=[:/."\s-]|$)' % re.escape(p['old_id']), p['new_id'], s)
    s = s.replace('"%s"' % p['old_name'], '"%s"' % p['new_name'])
    return s


def files_under(rel):
    base = os.path.join(ROOT, rel)
    for dp, _, fns in os.walk(base):
        for fn in fns:
            yield os.path.join(dp, fn)


def apply(p, dry):
    changes = []

    def edit(path, fn):
        old = open(path, encoding='utf-8').read()
        new = fn(old)
        if new != old:
            changes.append('edit ' + os.path.relpath(path, ROOT))
            if not dry:
                open(path, 'w', encoding='utf-8').write(new)

    def prop(s):
        s = re.sub(r'(?m)^mod_id=.*$', 'mod_id=' + p['new_id'], s)
        s = re.sub(r'(?m)^mod_name=.*$', 'mod_name=' + p['new_name'], s)
        s = re.sub(r'(?m)^mod_group_id=.*$', 'mod_group_id=' + p['new_pkg'], s)
        return rewrite_text(s, p)
    edit(os.path.join(ROOT, 'gradle.properties'), prop)
    edit(os.path.join(ROOT, 'settings.gradle'),
         lambda s: re.sub(r"rootProject\.name = '.*'", "rootProject.name = '%s'" % p['new_id'], s))

    for rel in SOURCE_ROOTS + RESOURCE_ROOTS:
        for path in files_under(rel):
            if path.endswith(TEXT_EXT):
                edit(path, lambda s: rewrite_text(s, p))

    # move folders: java packages, then assets/data namespaces, then the main class file
    moves = []
    for rel in SOURCE_ROOTS:
        src = os.path.join(ROOT, rel, *p['old_pkg'].split('.'))
        if os.path.isdir(src):
            moves.append((src, os.path.join(ROOT, rel, *p['new_pkg'].split('.'))))
    for rel in RESOURCE_ROOTS:
        for kind in ('assets', 'data'):
            src = os.path.join(ROOT, rel, kind, p['old_id'])
            if os.path.isdir(src):
                moves.append((src, os.path.join(ROOT, rel, kind, p['new_id'])))
    for src, dst in moves:
        changes.append('move %s -> %s' % (os.path.relpath(src, ROOT), os.path.relpath(dst, ROOT)))
        if not dry:
            if os.path.exists(dst):
                raise SystemExit('refusing to overwrite %s' % dst)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.move(src, dst)
            prune_empty(os.path.dirname(src))
    cls_old = os.path.join(ROOT, 'src/main/java', *p['new_pkg'].split('.'), p['old_cls'] + '.java')
    cls_new = os.path.join(os.path.dirname(cls_old), p['new_cls'] + '.java')
    if p['old_cls'] != p['new_cls']:
        changes.append('rename %s.java -> %s.java' % (p['old_cls'], p['new_cls']))
        if not dry:
            shutil.move(cls_old, cls_new)
    return changes


def prune_empty(d):
    while d.startswith(ROOT) and os.path.isdir(d) and not os.listdir(d) and \
            os.path.basename(d) not in ('java', 'assets', 'data'):
        os.rmdir(d)
        d = os.path.dirname(d)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('name', help='the display name, e.g. "Dragon Treasure"')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    try:
        p = plan(a.name.strip())
    except ValueError as e:
        print('rename-mod: ' + str(e), file=sys.stderr)
        return 2
    print('rename-mod: %s (%s, %s) -> %s (%s, %s, main class %s)' % (
        p['old_name'], p['old_id'], p['old_pkg'], p['new_name'], p['new_id'], p['new_pkg'], p['new_cls']))
    changes = apply(p, a.dry_run)
    for c in changes:
        print('  ' + c)
    print('rename-mod: %d change(s)%s' % (len(changes), ' (dry run, nothing written)' if a.dry_run else ''))
    if not a.dry_run:
        print('rename-mod: delete build/ and run/ before the next build: '
              'they hold the old name.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
