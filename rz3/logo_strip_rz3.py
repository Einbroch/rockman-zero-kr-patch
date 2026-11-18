"""3편 로고 등장 연출의 글자 띠 「ロックマンゼロ」 -> 「록맨 제로」 (스프라이트).

타이틀 직전 연출에서 글자들이 하나씩 날아와 「ロックマンゼロ」 띠가 되고, 이어서 「3」·Z 와 합쳐진다.
이 띠는 BG 로고(logo_rz3)와 다른 그림이다: OBJ 4bpp 타일 112장(서술자 0x5D849C -> 0x61A864 압축,
팔레트 0x61B11C, OBJ 팔레트 2), 1D 배치. 정지 배치는 스프라이트 20개(아래 REST, Mesen 덤프로 확인).

띠는 BG 로고 글자와 같은 자리에 ®·판·테두리 없이 그려져 있다(맞대어 확인). 일본어 로고 색 → 띠 색 대응도
같이 얻어, BG 로고와 같은 설계의 「록맨」「제로」(logo_glyphs, 늘림·기울임·그러데이션)를 띠 색으로 그린다.
스프라이트 배치는 코드가 정하므로 그대로 두고 글자를 LAYOUT 자리에 맞췄다(잘리는 픽셀 0 이 아니면 실패).
각 픽셀은 그 자리를 덮는 맨 위(번호가 작은) 스프라이트 타일에만 쓴다. 「3」 타일(0~47·80~83·109·110)은 그대로.
"""

import os
import struct
import sys
from collections import Counter

from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
import lz77
import logo_rz3
import logo_glyphs as LG
import logo_redraw as TL

DESCRIPTOR, TARGET = 0x5D849C, 0xFB0000   # 0xF60000~ 로고·안내·스크롤, 0xF90000~ 서브 화면
TILES = 112
# 정지 배치 (x, y, 폭, 높이, 첫 타일). 0~14 파랑 「ロックマン」, 15~19 주황 「ゼロ」
REST = [(16, 40, 32, 8, 68), (11, 42, 32, 16, 48), (56, 45, 8, 8, 111), (50, 45, 8, 16, 106),
        (34, 45, 16, 16, 76), (67, 51, 8, 8, 108), (54, 51, 16, 8, 96), (48, 41, 16, 16, 84),
        (64, 41, 16, 16, 88), (80, 52, 16, 8, 100), (93, 40, 8, 16, 104), (77, 40, 16, 16, 92),
        (96, 40, 32, 8, 56), (113, 42, 8, 16, 98), (97, 42, 16, 16, 60),
        (160, 36, 16, 8, 102), (132, 36, 32, 8, 64), (122, 42, 32, 16, 16), (155, 40, 32, 8, 72),
        (147, 42, 32, 16, 24)]
BLUE, ORANGE = range(0, 15), range(15, 20)
BAND = range(39, 60)
# 글자 자리 (글자들, x0, y 이동, 파랑?). 스프라이트 배치는 코드가 정해 바꾸지 않으므로 글자를 빈틈에 맞췄다:
# 주황 스프라이트(x 122~187)에는 한 글자만 들어가 「제」는 파랑 스프라이트 끝(x 88~123)에 둔다.
# 빈 곳: x 121 열(y 48~57), x 128~131 의 y 40~41, y 58 행. 「제로」는 y 58 을 피해 1px 위.
# 띄어쓰기(맨-제 약 9px) > 글자 사이(제-로 약 2px) 라 「록맨 제로」로 읽힌다.
LAYOUT = [(('rok', 'maen'), 11, 0, True), (('je',), 87, -1, False), (('ro',), 123, -1, False)]


def get_px(tiles, t, x, y):
    b = tiles[t * 32 + y * 4 + x // 2]
    return (b >> 4) if x & 1 else b & 15


def set_px(tiles, t, x, y, v):
    i = t * 32 + y * 4 + x // 2
    tiles[i] = (tiles[i] & 0x0F) | (v << 4) if x & 1 else (tiles[i] & 0xF0) | v


def cells(s):
    """스프라이트 s 의 (화면 x, y, 타일, 타일 안 x, y)"""
    x0, y0, w, h, t0 = REST[s]
    for y in range(h):
        for x in range(w):
            yield x0 + x, y0 + y, t0 + (y // 8) * (w // 8) + x // 8, x % 8, y % 8


def strip_image(tiles, zeros=False):
    """{(x, y): (색, 스프라이트)}. zeros: 스프라이트가 덮지만 투명한 칸도(맨 위 스프라이트 번호로)"""
    img = {}
    for s in reversed(range(len(REST))):   # 번호가 작은 스프라이트가 위
        for X, Y, t, x, y in cells(s):
            v = get_px(tiles, t, x, y)
            if v or (zeros and img.get((X, Y), (0,))[0] == 0):
                img[(X, Y)] = (v, s)
    return img


def logo_image(tiles, entries):
    def px(x, y):
        e = entries[(y // 8) * 32 + x // 8]
        return tiles[((e & 0x3FF) - 0x100) * 64 + (y % 8) * 8 + x % 8]
    return px


def align(jp_px, strip, group, xr):
    """띠 그룹(파랑/주황)과 일본어 로고를 맞대어 (dx, dy, {로고 색: 띠 색})"""
    pts = [(X, Y, v) for (X, Y), (v, s) in strip.items() if s in group]
    best = None
    for dy in range(-8, 9):
        for dx in range(-30, 31):
            pairs = Counter()
            for X, Y, v in pts:
                x, y = X - dx, Y - dy
                if y in BAND and xr[0] <= x <= xr[1]:
                    pairs[(jp_px(x, y), v)] += 1
                else:
                    pairs[(None, v)] += 1
            by = {}
            for (a, b), n in pairs.items():
                by.setdefault(a, Counter())[b] += n
            score = sum(c.most_common(1)[0][1] for a, c in by.items() if a is not None)
            if best is None or score > best[0]:
                best = (score, dx, dy, by)
    score, dx, dy, by = best
    cmap = {a: c.most_common(1)[0][0] for a, c in by.items() if a is not None}
    return dx, dy, cmap, score / len(pts)


def build(source):
    rel, size, layout = struct.unpack_from('<III', source, DESCRIPTOR)
    tiles, used = lz77.decompress(source, DESCRIPTOR + rel)
    if len(tiles) != TILES * 32 or used > size & 0x3FFFFF:
        raise ValueError('unexpected RZ3 logo strip tileset')
    jp_tiles, kr_tiles, entries, reg_jp, reg_kr = logo_rz3.korean(source)
    jp, kr = logo_image(jp_tiles, entries), logo_image(kr_tiles, entries)
    strip = strip_image(tiles, zeros=True)
    # 띠는 BG 로고 글자와 같은 자리(차이 0)에 그려져 있다 — 일본어 로고와 맞대어 확인
    for group, xr in ((BLUE, (0, reg_jp[0] - 1)), (ORANGE, (reg_jp[1] + 1, 239))):
        dx, dy, _, q = align(jp, strip, group, xr)
        if (dx, dy) != (0, 0) or q < 0.75:
            raise ValueError(f'logo strip no longer sits on the logo: {dx}, {dy}, {q:.3f}')
    # 글자: BG 로고와 같은 설계(logo_glyphs, 늘림·기울임·그러데이션). 자리는 LAYOUT.
    # 띠 원본처럼 테두리 없이 글자 채움만 그린다(테두리는 스프라이트 빈틈에서 잘려 들쭉날쭉해진다). ® 는 띠에 없다.
    S = logo_rz3.SPEC
    cmaps = {True: align(jp, strip, BLUE, (0, reg_jp[0] - 1))[2],
             False: align(jp, strip, ORANGE, (reg_jp[1] + 1, 239))[2]}
    owner = {}
    for s in reversed(range(len(REST))):
        for X, Y, t, x, y in cells(s):
            owner[(X, Y)] = s

    want = {}
    for glyph_list, x0, dy, blue in LAYOUT:
        bm = TL.widen(LG.word([getattr(LG, g)() for g in glyph_list], 2), S['widen'])
        grad = S['blue'] if blue else S['orange']
        cm = cmaps[blue]
        for y, row in enumerate(bm):
            shift = round((len(bm) - 1 - y) * S['slant'])
            for x, v in enumerate(row):
                if v:
                    c = TL.color(grad, S['top'] + y)   # 그러데이션은 글자 행 기준(BG 로고와 같은 색 순서)
                    if not cm.get(c):
                        raise ValueError(f'logo colour {c} has no strip colour')
                    want[(x0 + x + shift, S['top'] + y + dy)] = (cm[c], blue)
    new = bytearray(tiles)
    for s in range(len(REST)):
        for X, Y, t, x, y in cells(s):
            set_px(new, t, x, y, 0)
    lost = sorted(p for p in want if p not in owner)
    if lost:   # 글자 픽셀은 하나도 잘리면 안 된다
        raise ValueError(f'Korean logo strip clipped: {len(lost)} {lost[:6]}')
    for (X, Y), (v, blue) in want.items():
        x0, y0, w, h, t0 = REST[owner[(X, Y)]]
        x, y = X - x0, Y - y0
        set_px(new, t0 + (y // 8) * (w // 8) + x // 8, x % 8, y % 8, v)
    return tiles, bytes(new), dict(pixels=len(want))


HD = True        # 타이틀 로고가 사용자 HD 로고(logo_hd)이면 띠 글자도 그 글자로
HD_MAX_CLIP = 0.01   # 스프라이트 빈틈에 걸려 버리는 글자 픽셀 비율 상한(띠 → 타이틀 사이에 흰 번쩍임이 있어 작은 차이는 안 보인다)


def build_hd(source):
    """HD 로고의 「록맨」「제로」 채움(바깥 남색 테 제외, 원래 띠처럼)을 타이틀 로고 글자 자리에 블록째 줄여 놓는다.
    띠 스프라이트 영역(3,321px)이 원래 크기 글자보다 작고 빈틈이 있어 100% 로는 못 넣는다:
    크기를 1% 씩 줄이며 두 낱말을 각각 ±6px 안에서 옮겨 잘림이 HD_MAX_CLIP 이하인 가장 큰 크기를 고른다(잘린 픽셀은 버림)."""
    import numpy as np
    from scipy import ndimage
    import logo_hd
    rel, size, layout = struct.unpack_from('<III', source, DESCRIPTOR)
    tiles, used = lz77.decompress(source, DESCRIPTOR + rel)
    if len(tiles) != TILES * 32 or used > size & 0x3FFFFF:
        raise ValueError('unexpected RZ3 logo strip tileset')
    logo_rz3.hd_tiles(source)
    info = logo_rz3.hd_tiles.info
    (OX, OY), (W0, H0) = info['offset'], info['size']
    arr, fill = logo_hd.letters(3)
    arr = arr.astype(int)
    f0 = W0 / arr.shape[1]
    A = arr[..., 3] >= 128
    lab, n = ndimage.label(A, structure=np.ones((3, 3)))
    sizes = ndimage.sum(A, lab, range(1, n + 1))
    groups = [i + 1 for i in np.argsort(-sizes)[:2]]
    ys, xs = np.nonzero(A)
    bx, by = (xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2
    bcx, bcy = OX + bx * f0, OY + by * f0
    owner = {}
    for s in reversed(range(len(REST))):
        for X, Y, t, x, y in cells(s):
            owner[(X, Y)] = s
    pal = struct.unpack_from('<16H', source, 0x61B11C)
    rgb = [((c & 31) * 255 // 31, (c >> 5 & 31) * 255 // 31, (c >> 10 & 31) * 255 // 31) for c in pal]
    chosen = None
    for k in range(0, 31):
        sc = 0.9 - k * 0.01
        f = f0 * sc
        placed, total, clip = [], 0, 0
        for g in groups:
            m = (lab == g) & fill
            gy, gx = np.nonzero(m)
            x0, x1, y0, y1 = gx.min(), gx.max(), gy.min(), gy.max()
            sub = Image.fromarray(np.where(m[..., None], arr, 0).astype(np.uint8), 'RGBA').crop((x0, y0, x1 + 1, y1 + 1))
            w, h = max(1, round(sub.width * f)), max(1, round(sub.height * f))
            sm = np.asarray(sub.resize((w, h), Image.LANCZOS)).astype(int)
            py, px = np.nonzero(sm[..., 3] >= 128)
            tx, ty = bcx + (x0 - bx) * f, bcy + (y0 - by) * f
            best = None
            for dx in range(-6, 7):
                for dy in range(-6, 7):
                    ox, oy = round(tx) + dx, round(ty) + dy
                    c = sum((x + ox, y + oy) not in owner for x, y in zip(px, py))
                    key = (c, abs(dx) + abs(dy))
                    if best is None or key < best[0]:
                        best = (key, ox, oy)
            total += len(px)
            clip += best[0][0]
            placed.append((sm, px, py, best[1], best[2]))
        if clip <= total * HD_MAX_CLIP:
            chosen = (sc, placed, total, clip)
            break
    if not chosen:
        raise ValueError('RZ3 logo strip: HD letters do not fit the strip sprites')
    sc, placed, total, clip = chosen
    new = bytearray(tiles)
    for s in range(len(REST)):
        for X, Y, t, x, y in cells(s):
            set_px(new, t, x, y, 0)
    cache = {}
    for sm, px, py, ox, oy in placed:
        for x, y in zip(px, py):
            X, Y = x + ox, y + oy
            if (X, Y) not in owner:
                continue
            key = tuple(sm[y, x, :3])
            if key not in cache:
                r, g, b = key
                cache[key] = min(range(1, 16), key=lambda i: (rgb[i][0] - r) ** 2 * 3 + (rgb[i][1] - g) ** 2 * 4 + (rgb[i][2] - b) ** 2 * 2)
            x0, y0, w, h, t0 = REST[owner[(X, Y)]]
            lx, ly = X - x0, Y - y0
            set_px(new, t0 + (ly // 8) * (w // 8) + lx // 8, lx % 8, ly % 8, cache[key])
    print(f'RZ3 logo strip HD: scale {sc:.2f}, {total} px, clipped {clip}')
    return tiles, bytes(new), dict(pixels=total - clip, clipped=clip, scale=sc)


def apply(source, write):
    rel, size, layout = struct.unpack_from('<III', source, DESCRIPTOR)
    _, new, _ = build_hd(source) if HD else build(source)
    packed = lz77.compress(new)
    if lz77.decompress(packed)[0] != new:
        raise ValueError('RZ3 logo strip failed readback')
    write(TARGET, packed, 'RZ3 logo strip tiles')
    write(DESCRIPTOR, struct.pack('<III', TARGET - DESCRIPTOR, (size & ~0x3FFFFF) | len(packed), layout),
          'RZ3 logo strip descriptor')


if __name__ == '__main__':   # 미리 보기: python rz3/logo_strip_rz3.py out.png
    from PIL import Image
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
    src = open(os.path.join(root, 'roms', 'Rockman Zero 3 (Japan).gba'), 'rb').read()
    old, new, info = build(src)
    print(info)
    pal = struct.unpack_from('<16H', src, 0x61B11C)
    rgb = [((c & 31) * 8, (c >> 5 & 31) * 8, (c >> 10 & 31) * 8) for c in pal]
    out = Image.new('RGB', (200, 70), (0, 0, 0))
    for row, t in enumerate((old, new)):
        for (X, Y), (v, s) in strip_image(t).items():
            if 0 <= X - 5 < 200 and 0 <= Y - 32 + row * 35 < 70:
                out.putpixel((X - 5, Y - 32 + row * 35), rgb[v])
    out.resize((800, 280), Image.NEAREST).save(sys.argv[1])
