"""1편 타이틀 로고. BG2(256색, VRAM 0x4000) 타일은 롬 0x2F1294 에 무압축, 맵은 롬 0x2E008C(무압축 32x32)."""

import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
import logo_redraw as TL

TILES, MAP = 0x2F1294, 0x2E008C
LEFT = [14, 13, 12, 12, 11, 11, 10, 10, 9, 9, 9, 8, 8, 7, 7, 6, 6, 5, 5, 5, 5, 5, 5, 6]          # y 42..65
SPEC = dict(
    # y 41 은 「ゼ」 윗부분만 판 위로 튀어나와 있던 줄(x 158~193)
    y0=41, y1=65, left=lambda y: 158 if y == 41 else LEFT[y - 42],
    right=lambda y: 193 if y < 45 else min(int(194 - (y - 45) * 0.8), 181 if y > 61 else 999),
    plate=143, outline=142,
    blue={46: 131, 47: 125, 48: 121, 49: 121, 50: 114, 51: 110, 52: 101, 53: 101, 54: 94, 55: 85,
          56: 81, 57: 81, 58: 81, 59: 81, 60: 81, 61: 75, 62: 56},
    orange={44: 120, 45: 109, 46: 107, 47: 104, 48: 100, 49: 96, 50: 88, 51: 80, 52: 77, 53: 69,
            54: 70, 55: 66, 56: 63, 57: 60, 58: 60, 59: 58, 60: 58, 61: 58, 62: 51},
    registered=(126, 58, 134, 64), top=46, widen=1.6, slant=0.4, x1=16,
)


TILES_END = 0x2F5B54
HD = True   # 사용자 제작 HD 로고(art/logo_hd/zero1.png)로 통째로


def apply(rom, source):
    if HD:
        import logo_hd
        tiles = bytearray(source[TILES:TILES_END])
        rows = logo_hd.read_rows(source, MAP, 32, 32)
        info = logo_hd.compose(1, tiles, rows, 0)
        for a, b, new in ((TILES, TILES_END, bytes(tiles)), (MAP, MAP + 0x800, logo_hd.pack_rows(rows))):
            if rom[a:b] != source[a:b]:
                raise ValueError('title logo overlaps another build write')
            rom[a:b] = new
        return info['tiles']
    return apply_band(rom, source)


def apply_band(rom, source):
    entries = struct.unpack_from('<1024H', source, MAP)
    at = lambda x, y: TILES + (entries[(y // 8) * 32 + x // 8] & 0x3FF) * 64 + (y % 8) * 8 + x % 8
    changed = {}

    def put(x, y, v):
        changed[at(x, y)] = v
    tiles = TL.redraw(SPEC, entries, lambda x, y: source[at(x, y)], put)
    for offset, v in changed.items():
        if rom[offset] != source[offset]:
            raise ValueError(f'title logo overlaps another build write at {offset:#x}')
        rom[offset] = v
    return len(tiles)
