"""3편 타이틀 로고 「ロックマン®ゼロ」 -> 「록맨®제로」.

BG2(256색, char base 0x4000). 로고 타일은 VRAM 0x8000(타일 번호 0x100~)에 올라가는 압축 묶음
(서술자 0x5472A8 -> 0x548B84, 18,880바이트), 맵은 롬 0x522ED0 에 30열×20행 무압축.
글자 띠(y 39~59)를 판 색으로 지우고 tools/logo_redraw.py 로 다시 그린 뒤 다시 압축해 옮긴다.
"""

import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
import logo_redraw as TL
import lz77

DESCRIPTOR, MAP, TARGET = 0x5472A8, 0x522ED0, 0xF60000
LEFT = {39: 17, 40: 16, 41: 15, 42: 15, 43: 14, 44: 14, 45: 13, 46: 13, 47: 13, 48: 12, 49: 12,
        50: 11, 51: 11, 52: 10, 53: 10, 54: 10, 55: 10, 56: 10, 57: 10, 58: 9, 59: 10}
SPEC = dict(
    y0=40, y1=59, left=lambda y: LEFT[y], right=lambda y: 172,   # y 39 는 공유 타일(0x131·0x132) 행이라 제외
    plate=98, outline=99,
    blue={42: 117, 43: 124, 44: 130, 45: 135, 46: 139, 47: 143, 48: 148, 49: 158, 50: 158, 51: 165,
          52: 170, 53: 170, 54: 170, 55: 165, 56: 202},
    orange={42: 134, 43: 137, 44: 142, 45: 146, 46: 156, 47: 164, 48: 176, 49: 190, 50: 195, 51: 197,
            52: 197, 53: 197, 54: 197, 55: 197, 56: 206},
    registered=(118, 52, 127, 59), top=41, widen=1.4, slant=0.4, x1=17, reg_gap=6,
)


def apply(source, write):
    relative, size, layout = struct.unpack_from('<III', source, DESCRIPTOR)
    tiles, consumed = lz77.decompress(source, DESCRIPTOR + relative)
    if len(tiles) != 18880 or consumed > size & 0x3FFFFF:
        raise ValueError('unexpected RZ3 logo tileset')
    tiles = bytearray(tiles)
    rows = [struct.unpack_from('<30H', source, MAP + y * 60) for y in range(20)]
    entries = [row[x] if x < 30 else 0 for row in rows for x in range(32)]

    def at(x, y):
        tile = (entries[(y // 8) * 32 + x // 8] & 0x3FF) - 0x100
        if not 0 <= tile < len(tiles) // 64:
            raise ValueError(f'logo pixel ({x}, {y}) is outside the logo tileset')
        return tile * 64 + (y % 8) * 8 + x % 8

    def put(x, y, v):
        tiles[at(x, y)] = v
    TL.redraw(SPEC, entries, lambda x, y: tiles[at(x, y)], put)
    packed = lz77.compress(bytes(tiles))
    if lz77.decompress(packed)[0] != tiles:
        raise ValueError('RZ3 logo tileset failed readback')
    write(TARGET, packed, 'RZ3 logo tiles')
    write(DESCRIPTOR, struct.pack('<III', TARGET - DESCRIPTOR, (size & ~0x3FFFFF) | len(packed), layout),
          'RZ3 logo descriptor')
