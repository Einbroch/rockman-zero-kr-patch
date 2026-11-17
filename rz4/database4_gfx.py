"""4편 데이터베이스 화면의 BG 그림 글자 — 무압축 타일, ROM 제자리.

BG1 타일셋 기준(타일 0) = 0xB885D4. 데이터베이스 VRAM 덤프(BG1 타일 0x4000)와 414칸 바이트 일치로 확정했다.
- 아래 안내 줄 「✚ボタンの左右でタグのへんこうができます」: 18~19행, 타일 0x120~0x13D / 0x140~0x15D (30칸 x 2줄).
  글자는 시스템 문장 S31C 의 번역과 같게. 십자 아이콘(x 11~20)은 그대로 둔다.
- 위 탭 띠: 고른 탭마다 13x2 타일 띠가 따로 있다(보스 0x80, 적 A 0xC0, 적 B 0xE0, 기타 0x100; 아랫줄 +13).
  고른 탭 몸통(바탕 5)에 이름 전체(글자 f·테두리 2), 안 고른 탭(바탕 2)은 첫 글자가 탭 가장자리에서 잘려 보인다(글자 e·d·a).
  안 고른 탭 글자는 일본어 글자가 차지하던 상자 안에 한글 첫 글자를 같은 자리에서 시작해 그 상자에서 자른다.
  라틴 글자 A·B 는 그대로 둔다. 탭 장식(가장자리 b·c·3·6 등)은 바탕(2·5)이 아니라 건드리지 않는다.
상자 밖 픽셀이 바뀌면 실패한다.
"""

import gfxtext

BASE = 0xB885D4
HELP_TEXT = '버튼 좌우로 태그를 바꿉니다'
HELP = dict(rows=(0x120, 0x140), cols=30, rect=(23, 1, 230, 13), bg=1, fill=0xF, font='Galmuri11', height=11)

# (첫 타일, 고른 탭 이름, 고른 탭 몸통 x 범위, {안 고른 탭 글자 상자 x0: 한글 첫 글자 또는 None(그대로)})
TABS = [
    (0x80, '보스', (8, 47), {54: None, 70: None, 83: '기'}),
    (0xC0, '적 A', (24, 63), {17: '보', 70: None, 83: '기'}),
    (0xE0, '적 B', (40, 79), {17: '보', 27: '적', 83: '기'}),
    (0x100, '기타', (56, 95), {17: '보', 27: '적', 43: '적'}),
]
TAB_Y = (4, 14)                 # 탭 몸통 행(맨 위·아래 행은 테두리 자리)
SEL_BG, SEL_FILL, SEL_LINE = 5, 0xF, 2
OFF_BG, OFF_FILL = 2, 0xE
OFF_INK = {0xA, 0xD, 0xE}
GLYPH_Y = (5, 13)


def tile_grid(first, cols):
    return [list(range(first, first + cols)), list(range(first + (13 if cols == 13 else 0x20), first + (13 if cols == 13 else 0x20) + cols))]


def text_ink(text, font, height, bold=False, gap=1):
    tw, bm = gfxtext.text_bitmap(text, font, gap, bold, height)
    return tw, {(y, x) for y in range(height) for x in range(tw) if bm[y][x]}


# 라틴 A·B 는 원문 고른 탭(「エネミーA」「エネミーB」)의 끝 글자 픽셀을 그대로 쓴다: (띠 첫 타일, x0) 6px x 9행(5~13행)
LATIN_SRC = {'A': (0xC0, 54), 'B': (0xE0, 70)}
LATIN = {}


def load_latin(buf):
    for ch, (first, x0) in LATIN_SRC.items():
        c = gfxtext.canvas(buf, 0, [list(range(first, first + 13)), list(range(first + 13, first + 26))])
        ink = {(y, x) for y in range(9) for x in range(6) if c[5 + y][x0 + x] in (0xE, 0xF)}
        if not ink or c[5][x0 - 1] != SEL_LINE:
            raise ValueError(f'latin {ch} source moved')
        LATIN[ch] = (6, ink)


def tab_ink(text):
    """탭 글자: 한글은 굵게(원문 탭 글자처럼 2px 획), 라틴 A·B 는 원문 픽셀."""
    x, ink = 0, set()
    for k, ch in enumerate(text):
        if k:
            x += 1
        if ch == ' ':
            x += 2
            continue
        if ch in LATIN:
            w, part = LATIN[ch]
        else:
            w, part = text_ink(ch, 'Galmuri9', 9, bold=True)
        ink |= {(y, x + px) for y, px in part}
        x += w
    return x, ink


def write_back(buf, grid, c):
    for r, row in enumerate(grid):
        for i, t in enumerate(row):
            gfxtext.put_px(buf, 0, t, [c[r * 8 + y][i * 8:i * 8 + 8] for y in range(8)])


def draw_help(buf):
    grid = [list(range(HELP['rows'][0], HELP['rows'][0] + HELP['cols'])),
            list(range(HELP['rows'][1], HELP['rows'][1] + HELP['cols']))]
    c = gfxtext.canvas(buf, 0, grid)
    x0, y0, x1, y1 = HELP['rect']
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            if c[y][x] not in (HELP['bg'], 0xD, 0xF):
                raise ValueError(f'help line rect covers decoration at {x},{y}')
            c[y][x] = HELP['bg']
    tw, ink = text_ink(HELP_TEXT, HELP['font'], HELP['height'])
    if tw > x1 - x0:
        raise ValueError(f'help line {tw}px > {x1 - x0}px')
    top = y0 + (y1 - y0 + 1 - HELP['height']) // 2
    for y, x in ink:
        c[top + y][x0 + 1 + x] = HELP['fill']
    write_back(buf, grid, c)
    return grid, (x0, y0, x1, y1)


def draw_tabs(buf, first, name, body, heads):
    grid = [list(range(first, first + 13)), list(range(first + 13, first + 26))]
    c = gfxtext.canvas(buf, 0, grid)
    allowed = set()
    # 고른 탭: 몸통을 바탕 5 로 지우고 이름(글자 f, 테두리 2)
    bx0, bx1 = body
    y0, y1 = TAB_Y
    for y in range(y0, y1 + 1):
        for x in range(bx0, bx1 + 1):
            c[y][x] = SEL_BG
            allowed.add((y, x))
    avail = bx1 - bx0 + 1 - 2
    tw, ink = tab_ink(name)
    if tw > avail:
        raise ValueError(f'tab {name!r}: {tw}px > {avail}px')
    left = bx0 + 1 + (avail - tw) // 2
    pts = {(y0 + 1 + y, left + x) for y, x in ink}
    for y, x in pts:
        c[y][x] = SEL_FILL
    for y, x in pts:
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                p = (y + dy, x + dx)
                if p not in pts and y0 <= p[0] <= y1 and bx0 <= p[1] <= bx1:
                    c[p[0]][p[1]] = SEL_LINE
    # 안 고른 탭: 일본어 글자 상자(가로로 이어진 글자 픽셀 묶음)
    cols = sorted({x for y in range(GLYPH_Y[0], GLYPH_Y[1] + 1) for x in range(104)
                   if not bx0 <= x <= bx1 and c[y][x] in OFF_INK})
    boxes, cur = [], []
    for x in cols:
        if cur and x > cur[-1] + 2:
            boxes.append(cur); cur = []
        cur.append(x)
    if cur:
        boxes.append(cur)
    found = {b[0]: (b[0], b[-1]) for b in boxes}
    if sorted(found) != sorted(heads):
        raise ValueError(f'tab strip {first:#x}: glyph boxes {sorted(found)} != expected {sorted(heads)}')
    for x0, ch in heads.items():
        if ch is None:
            continue
        gx0, gx1 = found[x0]
        for y in range(GLYPH_Y[0], GLYPH_Y[1] + 1):
            for x in range(gx0, gx1 + 1):
                if c[y][x] in OFF_INK:
                    c[y][x] = OFF_BG
                if c[y][x] == OFF_BG:
                    allowed.add((y, x))
        _, gink = tab_ink(ch)
        for y, x in gink:
            Y, X = GLYPH_Y[0] + y, gx0 + x
            if X <= gx1 and c[Y][X] == OFF_BG:
                c[Y][X] = OFF_FILL
    write_back(buf, grid, c)
    return grid, allowed


def edit(rom):
    top = 0x160
    original = bytes(rom[BASE:BASE + top * 32])
    buf = bytearray(original)
    allowed = set()
    load_latin(original)
    grid, (x0, y0, x1, y1) = draw_help(buf)
    for r, row in enumerate(grid):
        for i, t in enumerate(row):
            allowed.update((t, y, x) for y in range(8) for x in range(8)
                           if x0 <= i * 8 + x <= x1 and y0 <= r * 8 + y <= y1)
    for first, name, body, heads in TABS:
        grid, ok = draw_tabs(buf, first, name, body, heads)
        for (Y, X) in ok:
            allowed.add((grid[Y // 8][X // 8], Y % 8, X % 8))
    for t in range(top):
        for y in range(8):
            for x in range(8):
                i = t * 32 + y * 4 + x // 2
                if (t, y, x) not in allowed and (original[i] ^ buf[i]) >> (x & 1) * 4 & 15:
                    raise ValueError(f'database: protected pixel changed tile {t:#x} ({x},{y})')
    return bytes(buf)


def apply(rom, write):
    new = edit(rom)
    old = rom[BASE:BASE + len(new)]
    runs, i = [], 0
    while i < len(new):
        if new[i:i + 32] != old[i:i + 32]:
            j = i
            while j < len(new) and new[j:j + 32] != old[j:j + 32]:
                j += 32
            runs.append((i, j)); i = j
        else:
            i += 32
    for a, b in runs:
        write(BASE + a, new[a:b], 'RZ4 database labels')
