"""4편 타이틀 로고 「ロックマン®ゼロ4」 -> 「록맨®제로4」.

BG2 256색. 타일 = LZ 묶음(서술자 0xB6C028 -> 0xB6DC24, 0x8000바이트, VRAM 0x8000 = 타일 0x100~),
맵 = ROM 0xB2CCE0(32열, 무압축), 팔레트 = ROM 0xB704CC.
글자는 파란(왼쪽)·노란(오른쪽) 판 위에 은색 획 + 검은 테두리로 그려져 있고, 판은 위아래로
검은 띠(37~38, 56~57행)·흰 줄(39, 54행)이 둘러싼다.
1) 지우기: 40~53행은 글자 픽셀(무채색)을 같은 행의 가장 가까운 판 픽셀로, 띠 행은 그 행의 주된 색으로 메운다.
2) 그리기: tools/logo_glyphs.py 의 「록맨」「제로」(18px 설계를 17px 로)를 41~57행에 은색 획·검은 테두리로 그린다.
   (37~39행 타일 0x131 은 맵에서 네 번 쓰이므로 건드리지 않는다 — 공유 타일이 바뀌면 빌드 실패.)
"""

import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
import logo_glyphs as LG
from logo_redraw import widen
import lz77

DESCRIPTOR, MAP, PALETTE = 0xB6C028, 0xB2CCE0, 0xB704CC
TARGET, ROOM = 0xDEF6FC, 0x2904            # 새 압축본을 둘 빈 조각
LEFT = dict(x0=10, x1=114, word=(lambda: rok17(), LG.maen), start=26, widen=1.5, gap=2)   # 파란 판 「ロックマン」
RIGHT = dict(x0=124, x1=168, word=(lambda: je17(), lambda: ro17()), start=125, widen=1.0, gap=1)  # 노란 판 「ゼロ」
FACE = range(40, 54)                       # 판 면(글자가 새겨진 행)
BANDS = (37, 38, 39, 54, 55, 56, 57)       # 띠 행
TOP, HEIGHT = 41, 17                       # 18px 설계를 17px 로: 40행에 검은 테두리가 들어가 39행 흰 줄과 떨어진다
EDGE = 0x61                                # 검은 테두리
SILVER = ((6, 0xCF), (11, 0xC1), (99, 0xB2))   # 획 안쪽 행 -> 색: 위 흰색, 아래로 갈수록 은회색


def rok17():
    """「록」 17px 설계: 18px 판을 줄이면 ㄹ 가로획 틈이 사라져 「로」처럼 보이므로 따로 그린다."""
    g = [[0] * 22 for _ in range(17)]
    def rect(x0, y0, x1, y1):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                g[y][x] = 1
    rect(2, 0, 18, 1); rect(17, 0, 18, 4); rect(2, 3, 18, 4); rect(2, 3, 3, 7); rect(2, 6, 18, 7)   # ㄹ
    rect(9, 8, 11, 8); rect(0, 9, 21, 10)                                                     # ㅗ
    rect(2, 12, 18, 13); rect(16, 12, 18, 16)                                                 # ㄱ
    return g


def _grid(w):
    g = [[0] * w for _ in range(17)]
    def rect(x0, y0, x1, y1):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                g[y][x] = 1
    return g, rect


def je17():
    """「제」 17px·폭 18: 오른쪽 노란 판이 좁아(45px) 18px 판을 줄이지 않고 따로 그린다."""
    g, rect = _grid(18)
    rect(0, 1, 10, 2)                                   # ㅈ 가로
    for k in range(13):                                 # ㅈ 두 다리
        y = 3 + k
        lx, rx = 5 - (k * 5) // 12, 5 + (k * 5) // 12
        rect(max(0, lx - 1), y, lx, y)
        rect(rx, y, min(10, rx + 1), y)
    rect(11, 7, 13, 8)                                  # ㅔ 짧은 가로
    rect(12, 0, 13, 16); rect(16, 0, 17, 16)            # ㅔ 세로 둘
    return g


def ro17():
    """「로」 17px·폭 18."""
    g, rect = _grid(18)
    rect(1, 0, 16, 1); rect(15, 0, 16, 4); rect(1, 3, 16, 4); rect(1, 3, 2, 8); rect(1, 7, 16, 8)   # ㄹ
    rect(8, 9, 10, 11)                                  # ㅗ 기둥
    rect(0, 12, 17, 14)                                 # ㅗ 가로
    return g


def fit(glyph):
    """18px 설계를 HEIGHT 로 세로 축소(이미 HEIGHT 면 그대로)."""
    h = len(glyph)
    return glyph if h == HEIGHT else [glyph[min(h - 1, round(y * (h - 1) / (HEIGHT - 1)))] for y in range(HEIGHT)]


def rgb(pal, i):
    c = pal[i * 2] | pal[i * 2 + 1] << 8
    return (c & 31) * 8, (c >> 5 & 31) * 8, (c >> 10 & 31) * 8


def grey(pal, i):
    """판 색(채도 높은 파랑·노랑·주황)이 아니면 글자(은색 획·테두리·흐린 가장자리)로 본다."""
    r, g, b = rgb(pal, i)
    return i == 0 or max(r, g, b) - min(r, g, b) < 60


HD = True   # 사용자 제작 HD 로고(art/logo_hd/zero4.png)로 통째로


def apply(rom, write):
    relative, size, layout = struct.unpack_from('<III', rom, DESCRIPTOR)
    tiles = bytearray(lz77.decompress(rom, DESCRIPTOR + relative)[0])
    if len(tiles) != 0x8000:
        raise ValueError('unexpected RZ4 logo tileset')
    if HD:
        import logo_hd
        original = bytes(tiles)
        rows = logo_hd.read_rows(rom, MAP, 32, 20)
        extra = struct.unpack_from('<384H', rom, MAP + 20 * 64)   # 20행 뒤(화면 밖)도 같은 타일을 쓰는지 센다
        logo_hd.compose(4, tiles, rows, 0x100, extra=extra)
        packed = lz77.compress(bytes(tiles))
        if lz77.decompress(packed)[0] != tiles:
            raise ValueError('RZ4 logo tileset failed readback')
        if len(packed) > ROOM or set(rom[TARGET:TARGET + ROOM]) != {0xFF}:
            raise ValueError(f'RZ4 logo does not fit its free area ({len(packed)} > {ROOM})')
        write(TARGET, packed, 'RZ4 logo tiles')
        write(DESCRIPTOR, struct.pack('<III', TARGET - DESCRIPTOR, (size & ~0x3FFFFF) | len(packed), layout),
              'RZ4 logo descriptor')
        write(MAP, logo_hd.pack_rows(rows), 'RZ4 title logo map')
        return original, bytes(tiles), [e for r in rows for e in r]
    pal = rom[PALETTE:PALETTE + 0x200]
    entries = [struct.unpack_from('<H', rom, MAP + i * 2)[0] for i in range(32 * 20)]
    uses = {}
    for e in entries:
        uses[e & 0x3FF] = uses.get(e & 0x3FF, 0) + 1

    def at(x, y):
        e = entries[(y // 8) * 32 + x // 8]
        if e & 0xC00:
            raise ValueError(f'flipped logo tile at ({x}, {y})')
        return ((e & 0x3FF) - 0x100) * 64 + (y % 8) * 8 + x % 8

    get = lambda x, y: tiles[at(x, y)]
    original = bytes(tiles)
    changed = set()

    def put(x, y, v):
        if tiles[at(x, y)] != v:
            tiles[at(x, y)] = v
            changed.add((x, y))

    for part in (LEFT, RIGHT):
        x0, x1 = part['x0'], part['x1']
        # 1) 판 면: 행마다 판 픽셀(유채색) 구간 안의 무채색 = 글자 -> 그 행 판 픽셀의 대표색(최빈값)
        #    (가장 가까운 픽셀을 복사하면 원래 글자 가장자리 무늬가 줄무늬로 남는다)
        for y in FACE:
            row = [get(x, y) for x in range(x0, x1 + 1)]
            plate = [i for i, v in enumerate(row) if not grey(pal, v)]
            if not plate:
                continue
            colors = [row[i] for i in plate]
            main = max(set(colors), key=colors.count)
            for i in range(plate[0], plate[-1] + 1):
                if grey(pal, row[i]):
                    put(x0 + i, y, main)
        # 띠 행: 판 면 구간 안에서 주된 색과 다른 픽셀을 주된 색으로
        span = range(x0 + 6, x1 + 1)
        for y in BANDS:
            row = [get(x, y) for x in span]
            main = max(set(row), key=row.count)
            for x, v in zip(span, row):
                shared = uses[entries[(y // 8) * 32 + x // 8] & 0x3FF] != 1   # 공유 타일(0x131 등)은 원래 띠라 그대로
                if v != main and grey(pal, v) and not shared:
                    put(x, y, main)
        # 2) 글자: 18px 설계를 16px 로 줄이고 기울여 은색 획 + 검은 테두리
        glyphs = [fit(g()) for g in part['word']]
        bm = widen([sum((g[y] + ([0] * part['gap'] if k < len(glyphs) - 1 else []) for k, g in enumerate(glyphs)), [])
                    for y in range(HEIGHT)], part['widen'])
        ink = set()
        for y, row in enumerate(bm):
            shift = round((HEIGHT - 1 - y) * 0.35)
            for x, v in enumerate(row):
                if v:
                    ink.add((TOP + y, part['start'] + x + shift))
        edge = {(y + dy, x + dx) for y, x in ink for dy in (-1, 0, 1) for dx in (-1, 0, 1)
                if TOP - 1 <= y + dy <= 57} - ink   # 39행(공유 타일 흰 줄)·58행(바깥 흰 테) 은 건드리지 않는다
        for y, x in edge | ink:
            if not (x0 <= x <= x1 and TOP - 1 <= y <= TOP + HEIGHT):
                raise ValueError(f'logo glyph leaves its plate at ({x}, {y})')
        for y, x in edge:
            put(x, y, EDGE)
        for y, x in ink:
            put(x, y, next(c for limit, c in SILVER if y - TOP < limit))
    for x, y in changed:
        t = entries[(y // 8) * 32 + x // 8] & 0x3FF
        if uses[t] != 1:
            raise ValueError(f'shared logo tile {t:#x} would change at ({x}, {y})')
    packed = lz77.compress(bytes(tiles))
    if lz77.decompress(packed)[0] != tiles:
        raise ValueError('RZ4 logo tileset failed readback')
    if len(packed) > ROOM or set(rom[TARGET:TARGET + ROOM]) != {0xFF}:
        raise ValueError(f'RZ4 logo does not fit its free area ({len(packed)} > {ROOM})')
    write(TARGET, packed, 'RZ4 logo tiles')
    write(DESCRIPTOR, struct.pack('<III', TARGET - DESCRIPTOR, (size & ~0x3FFFFF) | len(packed), layout),
          'RZ4 logo descriptor')
    return original, bytes(tiles), entries
