"""타이틀 로고를 사용자 제작 HD 한글 로고(art/logo_hd/zeroN.png)로 통째로 바꾼다 (1~4편 공용, GBA·컬렉션 공용).

로고는 256색 BG, 타일 수·맵 크기는 바꾸지 않는다(타일셋 뒤 VRAM 은 다른 층이 쓴다).
1. 타일 예산(P) = 맵 위쪽 로고 구역(TOP_ROWS 행 위, 30열 안)에서만 쓰이는 타일 번호(빈 칸 타일 제외).
   다른 구역·다른 맵 블록에서도 쓰이는 타일은 건드리지 않는다.
2. HD 로고를 원래 로고 상자(BOX) 비율로 줄이고(LANCZOS, 알파 128 이상만) 원래 로고 색 번호 중 가장 가까운 색으로.
   빈 자리는 빈 칸 타일의 같은 자리 값(1편 검정 바탕, 2~4편 0 = 투명).
   필요한 서로 다른 타일 수(같은 내용 칸은 한 타일 공유)가 P 를 넘으면 1% 씩 줄이고 조금씩 옮겨 가며 맞는 가장 큰 크기를 찾는다.
3. 새 로고 칸은 P 의 타일을 새로 배정(뒤집힘 없음), 나머지 로고 구역 칸 중 P 타일을 쓰던 칸은 빈 칸 항목으로.
팔레트(data/title_pal_rzN.json)는 Mesen 타이틀 화면 덤프에서 뽑았다(한글판에서 값이 바뀌는 칸은 쓰지 않는다).
"""
import json
import os
from collections import Counter

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
# 원래 로고(한글판) 덩어리 상자 (x0, y0, x1, y1) — 타이틀 화면 BG 덤프에서 바탕을 걷어 낸 경계
BOX = {1: (3, 8, 236, 100), 2: (8, 8, 231, 92), 3: (8, 7, 231, 90), 4: (8, 7, 231, 87)}
TOP_ROWS = 16          # 로고 구역: 0~15행(y < 128). 아래는 저작권·안내
ALPHA = 128


def palette(n):
    d = json.load(open(os.path.join(ROOT, 'data', f'title_pal_rz{n}.json')))
    rgb = [((c & 31) * 255 // 31, (c >> 5 & 31) * 255 // 31, (c >> 10 & 31) * 255 // 31) for c in d['bgr555']]
    return rgb, set(d['differs_in_korean'])


def art(n):
    a = Image.open(os.path.join(ROOT, 'art', 'logo_hd', f'zero{n}.png')).convert('RGBA')
    return a.crop(a.getbbox())


def render(img, w, h, allowed, rgb):
    """-> {(x, y): 색 번호} (불투명 픽셀만, 상대 좌표)"""
    small = img.resize((w, h), Image.LANCZOS)
    cand = sorted(allowed)
    cache, out, px = {}, {}, small.load()
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a < ALPHA:
                continue
            key = (r, g, b)
            if key not in cache:
                cache[key] = min(cand, key=lambda i: (rgb[i][0] - r) ** 2 * 3 + (rgb[i][1] - g) ** 2 * 4 + (rgb[i][2] - b) ** 2 * 2)
            out[(x, y)] = cache[key]
    return out


def compose(n, tiles, rows, tile0, base=0, extra=(), exclude=()):
    """tiles: bytearray(8bpp, 타일 k = base + (k - tile0) * 64), rows: 맵 행 목록(u16 목록, 30칸 이상, 20행 이상) — 제자리 수정,
    extra: 화면 밖 맵 항목(다른 블록 등, 사용만 센다). -> dict(scale, offset, size, tiles, cells, colors)"""
    rgb, unstable = palette(n)
    x0, y0, x1, y1 = BOX[n]
    blank = Counter(e for row in rows[:20] for e in row[:30]).most_common(1)[0][0]

    def off(e):
        k = (e & 0x3FF) - tile0
        if not 0 <= base + k * 64 <= len(tiles) - 64:
            raise ValueError(f'RZ{n} logo tile {e & 0x3FF:#x} outside tileset')
        return base + k * 64

    def px(x, y):
        return tiles[off(rows[y // 8][x // 8]) + (y % 8) * 8 + x % 8]

    region = [(cx, cy) for cy in range(TOP_ROWS) for cx in range(30)]
    inside, outside = Counter(), Counter()
    for cy, row in enumerate(rows):
        for cx, e in enumerate(row):
            ((inside if (cx, cy) in set(region) else outside))[e & 0x3FF] += 1
    for e in extra:
        outside[e & 0x3FF] += 1
    pool = sorted(t for t in inside if t not in outside and t != blank & 0x3FF)
    bg = bytes(tiles[off(blank):off(blank) + 64])
    allowed = {px(x, y) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)} - {0, *unstable, *exclude} - set(bg)
    if len(allowed) < 16:
        raise ValueError(f'RZ{n} logo: too few logo colours ({len(allowed)})')
    img = art(n)
    bw, bh = x1 - x0 + 1, y1 - y0 + 1
    fit = min(bw / img.width, bh / img.height)
    chosen = None
    for k in range(40):
        sc = 1 - k * 0.01
        w, h = round(img.width * fit * sc), round(img.height * fit * sc)
        ink0 = render(img, w, h, allowed, rgb)
        shifts = sorted(((dx, dy) for dx in range(-7, 8) for dy in range(-7, 8)), key=lambda t: (abs(t[0]) + abs(t[1]), t))
        for dx, dy in shifts:
            ox, oy = x0 + (bw - w) // 2 + dx, y0 + (bh - h) // 2 + dy
            if ox < 0 or oy < 0 or ox + w > 240 or oy + h > TOP_ROWS * 8:
                continue
            ink = {(ox + x, oy + y): v for (x, y), v in ink0.items()}
            cells = {(x // 8, y // 8) for x, y in ink}
            content = {}
            for cx, cy in cells:
                content[(cx, cy)] = bytes(ink.get((cx * 8 + i % 8, cy * 8 + i // 8), bg[i]) for i in range(64))
            uniq = sorted(set(content.values()))
            if len(uniq) <= len(pool):
                chosen = (sc, (ox, oy), (w, h), ink, content, uniq)
                break
        if chosen:
            break
    if not chosen:
        raise ValueError(f'RZ{n} logo: no fitting size')
    sc, (ox, oy), (w, h), ink, content, uniq = chosen
    tile_of = {c: pool[i] for i, c in enumerate(uniq)}
    poolset = set(pool)
    for cx, cy in region:
        e = rows[cy][cx]
        if (cx, cy) in content:
            rows[cy][cx] = (blank & 0xF000) | tile_of[content[(cx, cy)]]
        elif (e & 0x3FF) in poolset:
            rows[cy][cx] = blank
        elif e != blank and any(px(cx * 8 + i % 8, cy * 8 + i // 8) != bg[i] for i in range(64)):
            rows[cy][cx] = blank   # 다른 구역과 공유하는 타일의 옛 로고 조각: 타일은 두고 맵만 빈 칸으로
    for c, t in tile_of.items():
        o = off(t)
        tiles[o:o + 64] = c
    for t in pool[len(uniq):]:
        o = off(t)
        tiles[o:o + 64] = bg
    # 게이트: 새 로고 픽셀이 화면에 그대로, 로고 구역 밖 칸·예산 밖 타일은 그대로
    for (x, y), v in ink.items():
        if px(x, y) != v:
            raise ValueError(f'RZ{n} logo pixel ({x}, {y}) lost')
    return dict(scale=sc, offset=(ox, oy), size=(w, h), tiles=len(uniq), pool=len(pool), cells=len(content),
                colors=len(allowed), pool_ids=pool)


def read_rows(buf, addr, cols, nrows):
    import struct
    return [list(struct.unpack_from(f'<{cols}H', buf, addr + y * cols * 2)) for y in range(nrows)]


def pack_rows(rows):
    import struct
    return b''.join(struct.pack(f'<{len(r)}H', *r) for r in rows)


def preview(n, tiles, rows, tile0, base=0, path=None):
    rgb, _ = palette(n)
    im = Image.new('RGB', (240, 104))
    for y in range(104):
        for x in range(240):
            e = rows[y // 8][x // 8]
            im.putpixel((x, y), rgb[tiles[base + ((e & 0x3FF) - tile0) * 64 + (y % 8) * 8 + x % 8]])
    if path:
        im.resize((960, 416), Image.NEAREST).save(path)
    return im
