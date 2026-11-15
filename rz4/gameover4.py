"""4편 게임오버 「ゲームオーバー」 -> 「게임 오버」.

묶음 0xB91FD4(LZ, 0x1540바이트)는 2·3편과 같은 배치: 타일 0x0B~0x1C(윗줄)·0x2B~0x3C(아랫줄)이 맵에
순서대로 놓인 144x16 띠. 서술자는 0xB6C7F8(크기 0x57C — 2편과 같은 형식).
(0xB6C244 부근에도 이 묶음을 가리키는 자기상대 값이 잔뜩 있지만 크기 칸이 0인 빈 표라 쓰이지 않는다.)
새 압축본은 한글 구간 밖 빈 조각 0xC15C68(0x2398)에 둔다.
"""

import struct

import gfxtext
import lz77

DESCRIPTOR = 0xB6C7F8
SOURCE, TARGET, ROOM = 0xB91FD4, 0xC15C68, 0x2398
R = lambda a, b: list(range(a, b + 1))
GRID = [R(0x0B, 0x1C), R(0x2B, 0x3C)]


def apply(rom, write):
    rel, size, layout = struct.unpack_from('<III', rom, DESCRIPTOR)
    if DESCRIPTOR + rel != SOURCE or size != 0x57C:
        raise ValueError('unexpected game over descriptor')
    original = lz77.decompress(rom, SOURCE)[0]
    if len(original) != 0x1540:
        raise ValueError('unexpected game over tileset')
    before = gfxtext.canvas(bytearray(original), 0, GRID)
    if {v for row in before for v in row} != {0, 1, 2, 3}:
        raise ValueError('unexpected game over label colors')
    width, ink = gfxtext.text_bitmap('게임 오버', 'Galmuri11', 2, True, 11)
    ink = [[v for v in row for _ in (0, 1)] for row in ink]   # 가로 2배(원본의 굵은 가타카나 폭)
    width *= 2
    canvas = [[0] * 144 for _ in range(16)]
    left, top = (144 - width - 1) // 2, 2
    if left < 1:
        raise ValueError('game over label does not fit')
    for y, row in enumerate(ink):
        for x, v in enumerate(row):
            if v:
                canvas[top + y][left + x] = 1
    for y, row in enumerate(ink):
        for x, v in enumerate(row):
            if v and canvas[top + y + 1][left + x + 1] == 0:
                canvas[top + y + 1][left + x + 1] = 2
    assets = bytearray(original)
    for r, row in enumerate(GRID):
        for i, t in enumerate(row):
            gfxtext.put_px(assets, 0, t, [canvas[r * 8 + y][i * 8:i * 8 + 8] for y in range(8)])
    edited = {t for row in GRID for t in row}
    for t in range(len(original) // 32):
        if t not in edited and original[t * 32:t * 32 + 32] != assets[t * 32:t * 32 + 32]:
            raise ValueError(f'protected game over tile changed: {t:#x}')
    packed = lz77.compress(bytes(assets))
    if lz77.decompress(packed)[0] != assets or len(packed) > ROOM:
        raise ValueError('game over tileset failed readback or does not fit')
    if set(rom[TARGET:TARGET + ROOM]) != {0xFF}:
        raise ValueError('game over target area is not free')
    write(TARGET, packed, 'game over tileset')
    write(DESCRIPTOR, struct.pack('<III', TARGET - DESCRIPTOR, len(packed), layout), 'game over descriptor')
