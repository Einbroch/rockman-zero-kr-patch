"""초록 테두리 서브 화면(일반 미션)과 미션 결과 화면의 그림 글자.

첫 미션은 주황판(0x391850, screen_gfx.py)을 쓰고, 0x0202EBB4 비트1 이 꺼진 일반 미션은
아래 네 압축 타일셋을 따로 읽는다. 결과 화면(스크립트 명령 0x20)도 0x39188C 를 쓴다.

라벨 = 타일 격자 + 캔버스 안 사각형(rect, 포함 좌표) + 한국어.
사각형을 배경색으로 지우고 글자·그림자(오른쪽 아래)·외곽선을 그린다. 사각형 밖은 보존한다.
"""

import struct

import gfxtext
import lz77

R = lambda a, b: list(range(a, b + 1))

# (배경, 글자, 그림자, 외곽선 또는 None)
TAB = (7, 4, 8, 9)          # 청록 띠 위 큰 탭 글자
MENU = (9, 4, 8, None)      # 주황 상자 안 메뉴 글자
SMALL = (7, 3, 8, None)       # 상태 화면 작은 항목
OPTION = (8, 1, 7, None)    # 옵션 화면 항목 글자
RESULT = (9, 1, 8, None)    # 결과 화면 항목

ERASE = '\0'                # 글자 없이 지우기 (작은 「ボタン」)


def label(grid, rect, text, colors, font='Galmuri7', height=7, align='center', dy=0, **kw):
    return dict(grid=grid, rect=rect, text=text, colors=colors, font=font, height=height,
                align=align, dy=dy, **kw)


def big(grid, rect, text, colors=TAB, font=None, height=None, **kw):
    # 외곽선이 있으면 위아래 1px 씩 더 쓰므로 9px 글꼴을 쓴다.
    if font is None:
        font, height = ('Galmuri9', 9) if colors[3] is not None else ('Galmuri11', 11)
    return label(grid, rect, text, colors, font, height, **kw)


def strip(first, last, text, colors, align='left', rect=None):
    width = (last - first + 1) * 8
    return label([R(first, last)], rect or (0, 0, width - 1, 7), text, colors, align=align)


def two_rows(first, last):
    return [R(first, last), R(first + 0x20, last + 0x20)]


TILESETS = {
    # 상태 페이지
    0x391864: [
        big(two_rows(0x0A, 0x0E), (1, 2, 38, 12), '옵션', MENU),
        big(two_rows(0x4A, 0x4E), (1, 2, 38, 12), '폼', MENU),
        big(two_rows(0x8A, 0x8E), (1, 2, 38, 12), '상태', MENU),
        big(two_rows(0xCA, 0xCE), (0, 2, 39, 12), '엘프목록', MENU, font='Galmuri9', height=9, dy=1),
        big(two_rows(0x18, 0x1E), (4, 2, 46, 12), '폼'),
        label(two_rows(0x13, 0x17), (10, 8, 36, 12), ERASE, TAB),
        strip(0x53, 0x5B, '플레이 타임', SMALL, rect=(8, 0, 71, 7)),
        strip(0x96, 0x9D, '코드네임', SMALL, rect=(0, 0, 63, 7)),
        strip(0xF7, 0xFE, 'E크리스탈', SMALL, rect=(16, 0, 63, 7)),
        # ZERO 옆 「レベル」: 청록 띠(14) 위 주황(9) 글자, 두 타일 행에 걸친다.
        label(two_rows(0x150, 0x15A), (43, 4, 61, 13), '레벨', (14, 9, 14, None), font='Galmuri9', height=9),
        big(two_rows(0x1D1, 0x1DC), (2, 3, 49, 13), '엘프 목록', font='Galmuri9', height=9, dy=1),
        label(two_rows(0x1D1, 0x1DC), (66, 9, 91, 13), ERASE, TAB),
    ],
    # 폼 페이지
    0x391878: [
        big(two_rows(0x01, 0x0D), (18, 3, 59, 13), '상태'),
        label(two_rows(0x01, 0x0D), (74, 9, 99, 13), ERASE, TAB),
        big(two_rows(0x13, 0x1D), (38, 3, 80, 13), '옵션'),
        label(two_rows(0x13, 0x1D), (10, 9, 35, 13), ERASE, TAB),
        strip(0xC0, 0xC5, '폼', (7, 11, 8, None), align='center', rect=(4, 0, 47, 6)),
        strip(0xE0, 0xE5, 'EX 스킬', (7, 13, 8, None), align='center', rect=(4, 0, 47, 6)),
    ],
    # 옵션 페이지 + 미션 결과 화면
    0x39188C: [
        big(two_rows(0x01, 0x0D), (18, 3, 59, 13), '폼'),
        label(two_rows(0x01, 0x0D), (74, 9, 99, 13), ERASE, TAB),
        big(two_rows(0x13, 0x1E), (38, 3, 92, 13), '엘프 목록'),
        label(two_rows(0x13, 0x1E), (10, 9, 35, 13), ERASE, TAB),
        strip(0x46, 0x48, '타입', OPTION, 'right'),
        strip(0x49, 0x4C, '커스텀', OPTION, 'center'),
        strip(0x4D, 0x50, '대시', OPTION, 'center'),
        strip(0x51, 0x54, '점프', OPTION, 'center'),
        strip(0x60, 0x67, '메인 무기', OPTION, 'center'),
        strip(0x68, 0x6E, '서브 무기', OPTION, 'center'),
        strip(0x6F, 0x72, '버튼', OPTION),
        strip(0x80, 0x83, '전환', OPTION, 'center'),
        strip(0x86, 0x87, '서브', OPTION, 'center'),
        strip(0xA8, 0xB0, '버튼 설정', (7, 11, 8, None), 'center', rect=(14, 0, 65, 6)),
        strip(0xB1, 0xB9, '공격 모드', (7, 13, 8, None), 'center', rect=(3, 0, 68, 6)),
        big(two_rows(0x144, 0x14F), (1, 0, 93, 13), '결과', (8, 4, 6, 9), font='Galmuri11', height=11),
        strip(0x1C0, 0x1C4, '미션', RESULT),
        strip(0x1C5, 0x1CA, '클리어 타임', RESULT),
        strip(0x1CB, 0x1D2, '처치 수', RESULT),
        strip(0x1D3, 0x1D8, '받은 피해', RESULT),
        strip(0x1D9, 0x1DC, '재도전', RESULT),
        strip(0x1DD, 0x1DF, '엘프', RESULT),
        strip(0x1E0, 0x1E3, '합계', RESULT),
        strip(0x1E4, 0x1E7, '레벨', RESULT),
        strip(0x1E8, 0x1EE, '코드네임', RESULT),
        strip(0x1EF, 0x1F4, '획득한', RESULT),
        strip(0x1F7, 0x1F9, '스킬', RESULT),
        strip(0x1FA, 0x1FD, '폼', RESULT),
    ],
    # 엘프 목록 페이지
    0x3918A0: [
        big(two_rows(0x01, 0x0D), (18, 3, 59, 13), '옵션'),
        label(two_rows(0x01, 0x0D), (74, 9, 99, 13), ERASE, TAB),
        big(two_rows(0x41, 0x4E), (56, 3, 98, 13), '상태'),
        label(two_rows(0x41, 0x4E), (25, 9, 50, 13), ERASE, TAB),
    ],
}

# 라벨 스프라이트(엘프·서브 탱크 등): 16타일 행 다섯 개를 행마다 압축한 스트림.
SPRITE_DESCRIPTOR, SPRITE_STREAM = 0x43323C, 0x46878C
SPRITE = (0, 15, 13, 2)
SPRITE_LABELS = [
    dict(grid=[R(0, 4), R(16, 20)], rect=(2, 2, 37, 13), text='서브탱크', colors=SPRITE,
         font='Galmuri7', height=7, align='center', dy=1),
    dict(grid=[R(5, 9), R(21, 25)], rect=(2, 2, 37, 13), text='메인', colors=SPRITE,
         font='Galmuri9', height=9, align='center', dy=0),
    dict(grid=[R(10, 14), R(26, 30)], rect=(2, 2, 37, 13), text='엘프', colors=SPRITE,
         font='Galmuri9', height=9, align='center', dy=0),
    dict(grid=[R(32, 36), R(48, 52)], rect=(2, 2, 37, 13), text='서브', colors=SPRITE,
         font='Galmuri9', height=9, align='center', dy=0),
    dict(grid=[R(37, 41), R(53, 57)], rect=(2, 2, 37, 13), text='속성', colors=SPRITE,
         font='Galmuri9', height=9, align='center', dy=0),
    dict(grid=[R(42, 47), R(58, 63)], rect=(1, 4, 46, 15), text='탈출', colors=SPRITE,
         font='Galmuri9', height=9, align='center', dy=0),
]

def grid_bg(x, y):
    """통신 대전 제목 띠의 배경: 주황(9) 위 8px 간격 격자선(8), 교차점(7)."""
    return 7 if x % 8 == 3 and y % 8 == 3 else 8 if x % 8 == 3 or y % 8 == 3 else 9


RAINBOW = tuple(range(6, 16))    # 1P/2P 라벨: 글자마다 6~F 색이 왼쪽에서 오른쪽으로 바뀐다
LINK_SMALL = (9, 1, 11, None)    # 16px 높이 작은 글자 띠(한 글자 = 8x16)

# 통신 대전(타임 어택·에너미 배틀·아이템 겟) 화면. 맵 0x3882C8·0x3887D0·0x388CD8 에서 배치 확인.
TILESETS[0x3918B4] = [
    big(two_rows(0x10, 0x1F), (0, 3, 127, 15), '타임 어택', (grid_bg, 3, 5, 6), font='Galmuri11', height=11, gap=2),
    big(two_rows(0x50, 0x5F), (0, 3, 127, 15), '에너미 배틀', (grid_bg, 3, 5, 6), font='Galmuri11', height=11, gap=2),
    big(two_rows(0x90, 0x9F), (0, 3, 127, 15), '아이템 겟', (grid_bg, 3, 5, 6), font='Galmuri11', height=11, gap=2),
    big(two_rows(0xD5, 0xDF), (1, 1, 86, 12), '1 플레이어', (4, RAINBOW, 2, 5)),
    big(two_rows(0x115, 0x11F), (1, 1, 86, 12), '2 플레이어', (4, RAINBOW, 2, 5)),
    big(two_rows(0x193, 0x195), (0, 0, 23, 15), '구역', LINK_SMALL, align='left', dy=2),
    big(two_rows(0x196, 0x199), (0, 0, 31, 15), '격추', LINK_SMALL, align='right', dy=2),
    big(two_rows(0x19A, 0x19B), (0, 0, 15, 15), '수', LINK_SMALL, align='right', dy=2),   # 격추 수·획득 수 공유
    big(two_rows(0x19C, 0x19F), (0, 0, 31, 15), '합계', LINK_SMALL, align='left', dy=2),
    big(two_rows(0x1DC, 0x1DE), (0, 0, 23, 15), '획득', LINK_SMALL, align='left', dy=2),
    strip(0x1F5, 0x1FB, 'EC 획득!', (9, 1, 8, None)),
    label([R(0x124, 0x12B)], (16, 0, 63, 6), '폼', (3, 2, 3, None), align='left', keep_rows=(6,)),
]

TARGETS = {0x391864: 0xF40000, 0x391878: 0xF44000, 0x39188C: 0xF48000, 0x3918A0: 0xF4C000,
           0x3918B4: 0xF58000}


def draw(buf, spec):
    grid = spec['grid']
    c = gfxtext.canvas(buf, 0, grid)
    x0, y0, x1, y1 = spec['rect']
    bg, fill, shadow, outline = spec['colors']
    if not (0 <= x0 <= x1 < len(c[0]) and 0 <= y0 <= y1 < len(c)):
        raise ValueError(f'label rect outside its grid: {spec["text"]!r}')
    before = [row[:] for row in c]
    # bg 는 색 번호 또는 (x, y) -> 색 함수(격자 무늬 배경), fill 은 색 번호 또는 가로 그라데이션 색 목록.
    paint = bg if callable(bg) else (lambda x, y: bg)
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            c[y][x] = paint(x, y)
    if spec['text'] != ERASE:
        tw, bm = gfxtext.text_bitmap(spec['text'], spec['font'], spec.get('gap', 1), spec.get('bold', False),
                                     spec['height'])
        # 그림자가 배경과 같으면 그림자 칸을 비워 둘 필요가 없다.
        margin = (0 if shadow == bg else 1) if outline is None else 2
        avail = x1 - x0 + 1 - margin - (1 if outline is not None else 0)
        if tw > avail:
            raise ValueError(f'label {spec["text"]!r}: {tw}px > {avail}px')
        lead = 0 if outline is None else 1
        gap = avail - tw
        left = x0 + lead + (0 if spec['align'] == 'left' else gap if spec['align'] == 'right' else gap // 2)
        top = y0 + (0 if outline is None else 1) + spec['dy']
        if top + spec['height'] - 1 > y1:
            raise ValueError(f'label {spec["text"]!r} exceeds its rect height')
        ink = {(top + y, left + x) for y in range(spec['height']) for x in range(tw) if bm[y][x]}
        shade = {(y + dy, x + dx) for y, x in ink for dy, dx in ((1, 1), (0, 1), (1, 0))} - ink
        for y, x in ink:
            c[y][x] = fill[(x - left) * len(fill) // tw] if isinstance(fill, tuple) else fill
        for y, x in shade:
            if y0 <= y <= y1 and x0 <= x <= x1:
                c[y][x] = shadow
        if outline is not None:
            body = ink | {p for p in shade if y0 <= p[0] <= y1 and x0 <= p[1] <= x1}
            for y, x in body:
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        Y, X = y + dy, x + dx
                        if y0 <= Y <= y1 and x0 <= X <= x1 and (Y, X) not in body:
                            c[Y][X] = outline
    # 글자가 지나가지 않은 칸은 원본 줄(밑줄 등)을 되살린다.
    for y in spec.get('keep_rows', ()):
        for x in range(x0, x1 + 1):
            if c[y][x] == paint(x, y):
                c[y][x] = before[y][x]
    for r, row in enumerate(grid):
        for i, t in enumerate(row):
            gfxtext.put_px(buf, 0, t, [c[r * 8 + y][i * 8:i * 8 + 8] for y in range(8)])


def edit(source, descriptor):
    """원본 타일셋을 풀어 라벨을 그리고, 사각형 밖 픽셀이 그대로인지 확인한 결과를 돌려준다."""
    relative, size, layout = struct.unpack_from('<III', source, descriptor)
    original, consumed = lz77.decompress(source, descriptor + relative)
    if not 0 < consumed <= size & 0x3FFFFF:
        raise ValueError(f'unexpected tileset size at {descriptor:#x}')
    assets = bytearray(original)
    allowed = set()
    for spec in TILESETS[descriptor]:
        draw(assets, spec)
        x0, y0, x1, y1 = spec['rect']
        for r, row in enumerate(spec['grid']):
            for i, t in enumerate(row):
                for y in range(8):
                    for x in range(8):
                        if x0 <= i * 8 + x <= x1 and y0 <= r * 8 + y <= y1:
                            allowed.add((t, y, x))
    for t in range(len(original) // 32):
        for y in range(8):
            for x in range(8):
                index = t * 32 + y * 4 + x // 2
                shift = (x & 1) * 4
                if (t, y, x) not in allowed and (original[index] ^ assets[index]) >> shift & 15:
                    raise ValueError(f'protected pixel changed in {descriptor:#x} tile {t:#x}')
    return original, bytes(assets), size, layout


def sprite_rows(source):
    offset, flags = struct.unpack_from('<II', source, SPRITE_DESCRIPTOR)
    if SPRITE_DESCRIPTOR + offset != SPRITE_STREAM or flags != 0xA0000894:
        raise ValueError('unexpected green label sprite descriptor')
    cursor, rows = SPRITE_STREAM, []
    while cursor < SPRITE_STREAM + (flags & 0x3FFFFF):
        header, = struct.unpack_from('<I', source, cursor)
        chunk = source[cursor + 4:cursor + (header & 0x7FFFFFFF)]
        rows.append((header >> 31, lz77.decompress(chunk)[0] if header >> 31 else chunk))
        cursor += header & 0x7FFFFFFF
    if cursor != SPRITE_STREAM + (flags & 0x3FFFFF) or any(len(row) != 0x200 for _, row in rows):
        raise ValueError('green label sprite rows changed shape')
    return flags, rows


def edit_sprites(source):
    flags, rows = sprite_rows(source)
    original = b''.join(row for _, row in rows)
    sprites = bytearray(original)
    allowed = set()
    for spec in SPRITE_LABELS:
        draw(sprites, spec)
        x0, y0, x1, y1 = spec['rect']
        for r, row in enumerate(spec['grid']):
            for i, t in enumerate(row):
                allowed.update((t, y, x) for y in range(8) for x in range(8)
                               if x0 <= i * 8 + x <= x1 and y0 <= r * 8 + y <= y1)
    for t in range(len(original) // 32):
        for y in range(8):
            for x in range(8):
                index = t * 32 + y * 4 + x // 2
                if (t, y, x) not in allowed and (original[index] ^ sprites[index]) >> (x & 1) * 4 & 15:
                    raise ValueError(f'protected sprite pixel changed in tile {t:#x}')
    return flags, rows, original, bytes(sprites)


def apply_sprites(source, write):
    flags, rows, _, sprites = edit_sprites(source)
    stream = bytearray()
    for k, (compressed, _) in enumerate(rows):
        row = sprites[k * 0x200:(k + 1) * 0x200]
        if compressed:
            packed = lz77.compress(row)
            if lz77.decompress(packed)[0] != row:
                raise ValueError('green label sprite row failed readback')
            stream += struct.pack('<I', 0x80000000 | (len(packed) + 4)) + packed
        else:
            stream += struct.pack('<I', 0x204) + row
    target = 0xF50000
    write(target, stream, 'green label sprites')
    write(SPRITE_DESCRIPTOR, struct.pack('<II', target - SPRITE_DESCRIPTOR, (flags & ~0x3FFFFF) | len(stream)),
          'green label sprite descriptor')


def apply(source, write):
    for descriptor, target in TARGETS.items():
        _, assets, size, layout = edit(source, descriptor)
        packed = lz77.compress(assets)
        if lz77.decompress(packed)[0] != assets or len(packed) > 0x4000:
            raise ValueError(f'green sub-screen tileset {descriptor:#x} failed readback')
        write(target, packed, f'green sub-screen tileset {descriptor:#x}')
        write(descriptor, struct.pack('<III', target - descriptor, (size & ~0x3FFFFF) | len(packed), layout),
              f'green sub-screen descriptor {descriptor:#x}')
    apply_sprites(source, write)
    apply_gameover(source, write)


# 게임오버: 0x391E54 타일 0x0B~0x1C(윗줄)·0x2B~0x3C(아랫줄)이 BG2 맵에 순서대로 놓인 144x16 띠.
# 같은 타일셋의 Z 무늬는 통신 화면 배경으로도 쓰이므로 글자 타일만 바꾼다.
GAMEOVER_DESCRIPTOR = 0x391E54
GAMEOVER_GRID = [R(0x0B, 0x1C), R(0x2B, 0x3C)]


def edit_gameover(source):
    relative, size, layout = struct.unpack_from('<III', source, GAMEOVER_DESCRIPTOR)
    original, consumed = lz77.decompress(source, GAMEOVER_DESCRIPTOR + relative)
    if size != 0x57C or len(original) != 0x1540 or consumed > size:
        raise ValueError('unexpected game over tileset')
    before = gfxtext.canvas(original, 0, GAMEOVER_GRID)
    if {v for row in before for v in row} != {0, 1, 2, 3}:
        raise ValueError('unexpected game over label colors')
    width, ink = gfxtext.text_bitmap('게임 오버', 'Galmuri11', 2, True, 11)
    ink = [[v for v in row for _ in (0, 1)] for row in ink]   # 가로 2배: 원본의 굵은 가타카나 폭에 맞춘다
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
    for r, row in enumerate(GAMEOVER_GRID):
        for i, t in enumerate(row):
            gfxtext.put_px(assets, 0, t, [canvas[r * 8 + y][i * 8:i * 8 + 8] for y in range(8)])
    edited = {t for row in GAMEOVER_GRID for t in row}
    for t in range(len(original) // 32):
        if t not in edited and original[t * 32:t * 32 + 32] != assets[t * 32:t * 32 + 32]:
            raise ValueError(f'protected game over tile changed: {t:#x}')
    return original, bytes(assets), size, layout


def apply_gameover(source, write):
    _, assets, size, layout = edit_gameover(source)
    packed = lz77.compress(assets)
    if lz77.decompress(packed)[0] != assets:
        raise ValueError('game over tileset failed readback')
    target = 0xF54000
    write(target, packed, 'game over tileset')
    write(GAMEOVER_DESCRIPTOR, struct.pack('<III', target - GAMEOVER_DESCRIPTOR, len(packed), layout),
          'game over descriptor')
