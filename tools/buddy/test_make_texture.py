#!/usr/bin/env python3
"""make_texture.py writes a PNG whose pixels are exactly the text picture."""
import pathlib, struct, sys, tempfile, zlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import make_texture

ART = """# a tiny test picture
R = #ff0000
g = #00ff0080
. = #00000000
R.g
gR.
"""


def decode(data):
    """Just enough PNG reading to check what make_texture wrote."""
    assert data[:8] == b'\x89PNG\r\n\x1a\n', 'not a PNG'
    pos, idat, w, h = 8, b'', 0, 0
    while pos < len(data):
        n, kind = struct.unpack('>I4s', data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + n]
        assert struct.unpack('>I', data[pos + 8 + n:pos + 12 + n])[0] == zlib.crc32(kind + body) & 0xffffffff
        if kind == b'IHDR':
            w, h = struct.unpack('>II', body[:8])
        elif kind == b'IDAT':
            idat += body
        pos += 12 + n
    raw = zlib.decompress(idat)
    rows = [raw[y * (w * 4 + 1) + 1:(y + 1) * (w * 4 + 1)] for y in range(h)]
    return w, h, [[r[x * 4:x * 4 + 4] for x in range(w)] for r in rows]


def main():
    failures = []
    with tempfile.TemporaryDirectory() as d:
        src, out = pathlib.Path(d, 'a.txt'), pathlib.Path(d, 'a.png')
        src.write_text(ART)
        if make_texture.main(['x', str(src), str(out)]) != 0:
            failures.append('a good picture was refused')
        else:
            w, h, px = decode(out.read_bytes())
            if (w, h) != (3, 2): failures.append('size %dx%d, wanted 3x2' % (w, h))
            if px[0][0] != b'\xff\x00\x00\xff': failures.append('R is not solid red: %r' % px[0][0])
            if px[0][2] != b'\x00\xff\x00\x80': failures.append('g lost its see-through-ness: %r' % px[0][2])
            if px[1][2] != b'\x00\x00\x00\x00': failures.append('. is not invisible')
        src.write_text(ART + 'RRX\n')
        if make_texture.main(['x', str(src), str(out)]) == 0:
            failures.append('a letter missing from the palette was accepted')
        src.write_text(ART + 'RR\n')
        if make_texture.main(['x', str(src), str(out)]) == 0:
            failures.append('a short row was accepted')
    for f in failures:
        print('  ' + f)
    print('test_make_texture: ' + ('FAIL' if failures else 'PASS'))
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
