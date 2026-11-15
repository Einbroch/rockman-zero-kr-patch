"""3편 타이틀 시작 안내 「スタートボタンをおしてください」 -> 「스타트 버튼을 눌러 주세요」.

BG0·BG1 맵 14~15행이 타일 0x16,0x01~0x15 / 0x20~0x35(4bpp, 팔레트 15)를 순서대로 놓은 176x16 띠다.
타일은 타이틀 묶음(서술자 0x5472BC -> 0x54B174, VRAM 0x4000)에 있고 이 안내 말고는 쓰이지 않는다.
"""

import struct

import gfxtext
import lz77

DESCRIPTOR, TARGET = 0x5472BC, 0xF64000
GRID = [[0x16] + list(range(0x01, 0x16)), list(range(0x20, 0x36))]
TEXT = '스타트 버튼을 눌러 주세요'
FILL = [12, 12, 11, 11, 11, 9, 9, 9, 7, 7, 7]   # 위(밝은 하늘색) -> 아래(하늘색)
OUTLINE = 2


def apply(source, write):
    relative, size, layout = struct.unpack_from('<III', source, DESCRIPTOR)
    tiles, consumed = lz77.decompress(source, DESCRIPTOR + relative)
    if len(tiles) != 0x3F00 or consumed > size & 0x3FFFFF:
        raise ValueError('unexpected RZ3 title tileset')
    tiles = bytearray(tiles)
    width, ink = gfxtext.text_bitmap(TEXT, 'Galmuri11', 1, False, 11)
    canvas = [[0] * 176 for _ in range(16)]
    left, top = (176 - width) // 2, 2
    if left < 2:
        raise ValueError('title prompt does not fit')
    body = {(top + y, left + x) for y, row in enumerate(ink) for x, v in enumerate(row) if v}
    for y, x in body:
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if (y + dy, x + dx) not in body:
                    canvas[y + dy][x + dx] = OUTLINE
    for y, x in body:
        canvas[y][x] = FILL[y - top]
    for r, row in enumerate(GRID):
        for i, t in enumerate(row):
            gfxtext.put_px(tiles, 0, t, [canvas[r * 8 + y][i * 8:i * 8 + 8] for y in range(8)])
    packed = lz77.compress(bytes(tiles))
    if lz77.decompress(packed)[0] != tiles:
        raise ValueError('RZ3 title tileset failed readback')
    write(TARGET, packed, 'RZ3 title prompt tiles')
    write(DESCRIPTOR, struct.pack('<III', TARGET - DESCRIPTOR, (size & ~0x3FFFFF) | len(packed), layout),
          'RZ3 title prompt descriptor')
