"""그림 글자(타일에 구워진 라벨)를 한글로 다시 그리기.

라벨 = 타일 격자(행마다 타일 번호 목록) + 다시 그릴 띠(y0~y1, 8줄) + 한국어 + 정렬.
색은 원본 띠에서 뽑는다: 배경 = 가장 많은 색, 글자 = 다음, 그림자 = 그다음 (또는 명시).
글자는 7줄(Galmuri7) + 그림자(오른쪽·아래 1px). 띠 밖 행(장식)은 그대로 둔다.
"""
import os, sys
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kfont

_FONTS = {}


def font(name):
    if name not in _FONTS:
        root = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'external', 'fonts')
        _FONTS[name] = kfont.load_bdf(os.path.join(root, name + '.bdf'))
    return _FONTS[name]


def get_px(buf, off, t):
    base = off + t * 32
    return [[(buf[base + y * 4 + x // 2] >> ((x & 1) * 4)) & 15 for x in range(8)] for y in range(8)]


def put_px(buf, off, t, px):
    base = off + t * 32
    for y in range(8):
        for x in range(0, 8, 2):
            buf[base + y * 4 + x // 2] = px[y][x] | px[y][x + 1] << 4


def canvas(buf, off, grid):
    H = len(grid) * 8; W = max(len(r) for r in grid) * 8
    c = [[0] * W for _ in range(H)]
    for r, row in enumerate(grid):
        for i, t in enumerate(row):
            if t is None:
                continue
            px = get_px(buf, off, t)
            for y in range(8):
                for x in range(8):
                    c[r * 8 + y][i * 8 + x] = px[y][x]
    return c


def text_bitmap(text, fname='Galmuri7', gap=1, bold=False, height=7):
    """지정한 높이의 기준선에 맞춰 글리프를 배치한다."""
    g = font(fname)
    cols = []
    for k, ch in enumerate(text):
        if ch == ' ':
            cols += [[0] * height] * 3
            continue
        dw, w, h, xo, yo, rows, bits = g[ord(ch)]
        glyph = [[0] * max(w + max(xo, 0), 1) for _ in range(height)]
        for r, bitsrow in enumerate(rows):
            y = height - yo - h + r
            for x in range(w):
                if bitsrow >> (bits - 1 - x) & 1:
                    if not 0 <= y < height:
                        raise ValueError(f"glyph {ch!r} exceeds {height}px height")
                    glyph[y][x + max(xo, 0)] = 1
        if bold:   # 가로로 1px 겹쳐 굵게
            glyph = [r + [0] for r in glyph]
            glyph = [[r[x] | (r[x - 1] if x else 0) for x in range(len(r))] for r in glyph]
        for x in range(len(glyph[0])):
            cols.append([glyph[y][x] for y in range(height)])
        if k != len(text) - 1:
            cols += [[0] * height] * gap
    W = len(cols)
    return W, [[cols[x][y] for x in range(W)] for y in range(height)]


def draw_label(buf, off, spec):
    """spec: grid, band=(y0,y1 포함), text, align('left'|'center'|'right'), colors=(bg,fill,shadow) 또는 None, pad=(왼,오른)"""
    grid = spec['grid']
    c = canvas(buf, off, grid)
    y0, y1 = spec.get('band', (0, 7))
    W = len(c[0])
    if spec.get('colors'):
        bg, fill, shadow = spec['colors']
    else:
        cnt = Counter(c[y][x] for y in range(y0, y1 + 1) for x in range(W))
        order = [k for k, _ in cnt.most_common()]
        bg = order[0]; fill = order[1] if len(order) > 1 else 1; shadow = order[2] if len(order) > 2 else bg
    height = spec.get('height', 7)
    tw, bm = text_bitmap(spec['text'], spec.get('font', 'Galmuri7'), spec.get('gap', 1), spec.get('bold', False), height)
    pl, pr = spec.get('pad', (0, 0))
    avail = W - pl - pr - 1     # 그림자 1px
    if tw > avail:
        raise ValueError(f"label {spec['text']!r}: {tw}px > {avail}px")
    align = spec.get('align', 'center')
    x0 = pl + (0 if align == 'left' else (avail - tw) if align == 'right' else (avail - tw) // 2)
    x0 += spec.get('dx', 0)
    if x0 < pl or x0 + tw >= W - pr:
        raise ValueError(f"label {spec['text']!r} exceeds its tile columns")
    top = y0 + spec.get('dy', 0)
    if not 0 <= y0 <= top <= top + height - 1 <= y1 < len(c):
        raise ValueError(f"label {spec['text']!r} exceeds its tile rows")
    # 띠 지우기
    for y in range(y0, y1 + 1):
        for x in range(pl, W - pr):
            c[y][x] = bg
    for y in range(height):
        for x in range(tw):
            if bm[y][x]:
                Y, X = top + y, x0 + x
                c[Y][X] = fill
    for y in range(height):
        for x in range(tw):
            if bm[y][x]:
                for dy, dx in ((1, 1), (0, 1), (1, 0)):
                    Y, X = top + y + dy, x0 + x + dx
                    if y0 <= Y <= y1 and X < W - pr and c[Y][X] == bg:
                        c[Y][X] = shadow
    for r, row in enumerate(grid):
        for i, t in enumerate(row):
            if t is None:
                if any(c[r * 8 + y][i * 8:i * 8 + 8].count(bg) != 8 for y in range(8)):
                    raise ValueError(f"label {spec['text']!r} crosses a shared tile")
                continue
            put_px(buf, off, t, [c[r * 8 + y][i * 8:i * 8 + 8] for y in range(8)])
