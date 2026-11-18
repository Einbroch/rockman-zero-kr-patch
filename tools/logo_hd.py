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


def letters(n, width=700):
    """HD 로고에서 「록맨」「제로」 글자만 떼어 낸다(로고 등장 연출의 글자 띠용).
    -> (RGBA 배열(width 폭, 글자 밖은 투명), 채움 마스크(바깥 남색 테 제외)).
    글자 구조(실측): 바깥 남색 → 흰 테 → 안쪽 남색 → 흰 하이라이트 → 채움. 남색(밝기 < 45)을 벽으로 나눈 영역 중
    「록맨」(왼쪽 파랑) 세로 범위 안에 들고 대부분 흰색이 아닌 것 = 글자. Z 의 영역은 범위를 벗어나 빠진다."""
    import numpy as np
    from collections import deque
    from scipy import ndimage
    a = art(n)
    a = np.asarray(a.resize((width, round(a.height * width / a.width)), Image.LANCZOS)).astype(int)
    H, W = a.shape[:2]
    R, G, B, A = a[..., 0], a[..., 1], a[..., 2], a[..., 3]
    mx = np.maximum(np.maximum(R, G), B)
    mn = np.minimum(np.minimum(R, G), B)
    lum = 0.3 * R + 0.59 * G + 0.11 * B
    white = (A >= 128) & (mn > 190) & (mx - mn < 45)
    navy = (A >= 128) & (lum < 45)
    lab, k = ndimage.label(~(navy | (A < 128)))
    comps = ndimage.find_objects(lab)
    blue = B > R + 40
    info = []
    for i, sl in enumerate(comps, 1):
        if sl is None:
            continue
        m = lab[sl] == i
        cnt = int(m.sum())
        info.append((i, cnt, sl[1].start, sl[1].stop - 1, sl[0].start, sl[0].stop - 1,
                     blue[sl][m].mean(), white[sl][m].mean()))
    bl = [c for c in info if c[1] > 40 and c[3] < W * 0.42 and c[6] > 0.6]
    if not bl:
        raise ValueError(f'RZ{n} logo letters: no blue word found')
    y0 = min(c[4] for c in bl) - 30
    y1 = max(c[5] for c in bl) + 12
    keep_ids = [c[0] for c in info if c[1] > 20 and c[4] >= y0 and c[5] <= y1 and c[2] < W * 0.75
                and c[5] - c[4] >= 3 and c[7] < 0.5]
    keep = np.isin(lab, keep_ids)
    # 왼쪽(「록맨」) 파랑 채움은 하이라이트와 이어져 빠질 수 있어 따로 더한다(뒤에 Z 가 없다)
    yl = max(c[5] for c in bl)
    left = np.zeros((H, W), bool)
    left[y0:yl + 1, :int(W * 0.42)] = True
    bluefill = blue & (lum >= 60) & ~white & (A >= 128)
    fill = keep | (left & bluefill)
    full = fill | (ndimage.binary_dilation(fill, iterations=3) & navy)
    out = np.zeros_like(a)
    out[full] = a[full]
    return out.astype(np.uint8), fill
