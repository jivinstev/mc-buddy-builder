#!/usr/bin/env python3
"""Turn a text picture into a Minecraft texture (a PNG), with no image library needed.

    python3 tools/buddy/make_texture.py art/launch_pad.txt src/main/resources/assets/<modid>/textures/block/launch_pad.png

The text file is a palette, then the picture, one character per pixel (16 rows of 16 for a block):

    # comments start with #
    P = #863cc8
    Y = #ffe65a
    . = #00000000  # 8 hex digits: the last two are see-through-ness, 00 = invisible

    PPPPPPPPPPPPPPPP
    PPPPPPPYYPPPPPPP
    ...

Any character but # can be a pixel. Keep the .txt in art/ next to the project: change a letter, run this again, and the texture follows.
"""
import re, struct, sys, zlib

PALETTE_RE = re.compile(r'^(\S)\s*=\s*#([0-9a-fA-F]{6}(?:[0-9a-fA-F]{2})?)\s*$')


def parse(text):
    palette, rows = {}, []
    for raw in text.splitlines():
        line = raw.split('  #')[0].rstrip() if not raw.startswith('#') else ''
        if not line.strip():
            continue
        m = PALETTE_RE.match(line.strip())
        if m and not rows:
            hexcode = m.group(2) + ('ff' if len(m.group(2)) == 6 else '')
            palette[m.group(1)] = bytes.fromhex(hexcode)
        else:
            rows.append(line.strip())
    if not rows:
        raise ValueError('no picture rows found')
    width = len(rows[0])
    for i, r in enumerate(rows):
        if len(r) != width:
            raise ValueError('row %d is %d wide, row 1 is %d' % (i + 1, len(r), width))
        for c in r:
            if c not in palette:
                raise ValueError('row %d uses %r, which the palette does not name' % (i + 1, c))
    return palette, rows


def png(palette, rows):
    raw = b''.join(b'\x00' + b''.join(palette[c] for c in r) for r in rows)
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)
    header = struct.pack('>IIBBBBB', len(rows[0]), len(rows), 8, 6, 0, 0, 0)  # 8-bit RGBA
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', header) + chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b'')


def main(argv):
    if len(argv) != 3:
        print(__doc__.strip().split('\n\n')[1])
        return 2
    try:
        palette, rows = parse(open(argv[1], encoding='utf-8').read())
    except (OSError, ValueError) as e:
        print('make_texture: %s: %s' % (argv[1], e))
        return 1
    with open(argv[2], 'wb') as f:
        f.write(png(palette, rows))
    print('make_texture: %s -> %s (%dx%d)' % (argv[1], argv[2], len(rows[0]), len(rows)))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
