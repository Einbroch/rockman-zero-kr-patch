"""록맨 제로 타이틀 로고의 「ロックマン®ゼロ」 글자 띠를 「록맨®제로」로 다시 그린다(1·2편 공용).

로고는 256색 BG 이고, 띠 구역의 타일은 맵에서 한 번씩만 쓰여 맵을 바꾸지 않고 픽셀만 바꾼다.
get/put 은 화면 좌표 → 타일셋 바이트 접근을 넘겨받는다. 글자 모양은 logo_glyphs.py.
"""

import logo_glyphs as LG


def color(grad, y):
    keys = sorted(grad)
    return grad[y] if y in grad else grad[min(max(y, keys[0]), keys[-1])]


def widen(bm, factor):
    n = int(len(bm[0]) * factor)
    return [[row[int(x / factor)] for x in range(n)] for row in bm]


def redraw(spec, entries, get, put):
    """spec: y0,y1, left(y), right(y), plate, outline, blue, orange, registered(x0,y0,x1,y1),
    top, widen, slant, x1. entries: 맵 u16 목록(32열). 바꾼 픽셀이 쓰는 타일 번호 집합을 돌려준다."""
    y0, y1 = spec['y0'], spec['y1']
    rx0, ry0, rx1, ry1 = spec['registered']
    reg = [[get(x, y) for x in range(rx0, rx1 + 1)] for y in range(ry0, ry1 + 1)]
    words = (widen(LG.word([LG.rok(), LG.maen()], 2), spec['widen']),
             widen(LG.word([LG.je(), LG.ro()], 2), spec['widen']))
    reg_x = spec['x1'] + len(words[0][0]) + spec.get('reg_gap', 3)
    starts = (spec['x1'], reg_x + len(reg[0]) + 4)
    ink = {}
    for bm, x0, grad in zip(words, starts, (spec['blue'], spec['orange'])):
        h = len(bm)
        for y, row in enumerate(bm):
            shift = round((h - 1 - y) * spec['slant'])
            for x, v in enumerate(row):
                if v:
                    ink[(spec['top'] + y, x0 + x + shift)] = color(grad, spec['top'] + y)
    edge = {(y + dy, x + dx) for y, x in ink for dy in (-1, 0, 1) for dx in (-1, 0, 1)} - set(ink)
    inside = lambda x, y: y0 <= y <= y1 and spec['left'](y) <= x <= spec['right'](y)
    for y, x in edge | set(ink):
        if not inside(x, y):
            raise ValueError(f'title logo glyph leaves the plate at ({x}, {y})')
    new_reg = {(reg_x + dx, ry0 + dy): v for dy, row in enumerate(reg) for dx, v in enumerate(row)}
    for (x, y) in new_reg:
        if not inside(x, y) or (y, x) in ink or (y, x) in edge:
            raise ValueError('title logo registered mark overlaps')
    written = set()
    for y in range(y0, y1 + 1):
        for x in range(spec['left'](y), spec['right'](y) + 1):
            put(x, y, spec['plate']); written.add((x, y))
    for y, x in edge:
        put(x, y, spec['outline'])
    for (y, x), v in ink.items():
        put(x, y, v)
    for (x, y), v in new_reg.items():
        put(x, y, v)
    used = [e & 0x3FF for e in entries]
    tiles = {used[(y // 8) * 32 + x // 8] for x, y in written}
    for t in tiles:
        if used.count(t) != 1:
            raise ValueError(f'title logo tile {t:#x} is shared')
    if any(entries[(y // 8) * 32 + x // 8] & 0x0C00 for x, y in written):
        raise ValueError('title logo uses flipped tiles')
    return tiles
