"""2편 타이틀 로고. 타일 = 타이틀 타일셋(서술자 0x391EA4, VRAM 0x4000), 맵 = 롬 0x3873B0(무압축)."""

import struct
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
import logo_redraw as TL

MAP = 0x3873B0
LEFT = [17, 17, 17, 16, 15, 15, 14, 14, 13, 13, 13, 12, 12, 11, 11, 10, 10, 10, 9, 9, 10, 11]   # y 40..61
SPEC = dict(
    y0=40, y1=61, left=lambda y: LEFT[y - 40], right=lambda y: int(191 - (y - 43) * 0.9) - 3,
    plate=129, outline=128,
    blue={43: 140, 44: 146, 45: 146, 46: 154, 47: 154, 48: 163, 49: 163, 50: 172, 51: 180, 52: 180,
          53: 185, 54: 185, 55: 185, 56: 185, 57: 185, 58: 230},
    orange={42: 168, 43: 160, 44: 168, 45: 173, 46: 177, 47: 182, 48: 190, 49: 196, 50: 206, 51: 216,
            52: 221, 53: 225, 54: 228, 55: 228, 56: 228, 57: 228, 58: 220},
    registered=(122, 56, 130, 61), top=42, widen=1.5, slant=0.4, x1=17,
)


HD = True   # 사용자 제작 HD 로고(art/logo_hd/zero2.png)로 통째로


def apply(raw, source, write=None):
    if HD:
        import logo_hd
        raw = bytearray(raw)
        rows = logo_hd.read_rows(source, MAP, 32, 32)
        extra = struct.unpack_from('<1024H', source, MAP + 0x800)   # 두 번째 블록(메뉴 화면)도 같은 타일을 쓴다
        logo_hd.compose(2, raw, rows, 0, extra=extra)
        if write is None:
            raise ValueError('RZ2 HD logo needs write for the map')
        write(MAP, logo_hd.pack_rows(rows), 'RZ2 title logo map')
        return bytes(raw)
    return apply_band(raw, source)


def apply_band(raw, source):
    raw = bytearray(raw)
    entries = struct.unpack_from('<1024H', source, MAP)
    at = lambda x, y: (entries[(y // 8) * 32 + x // 8] & 0x3FF) * 64 + (y % 8) * 8 + x % 8

    def put(x, y, v):
        raw[at(x, y)] = v
    TL.redraw(SPEC, entries, lambda x, y: raw[at(x, y)], put)
    return bytes(raw)
