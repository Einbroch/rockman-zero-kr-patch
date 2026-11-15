"""일본판의 서브 화면·타이틀에 쓰이는 비압축 4bpp 타일 라벨."""

import gfxtext

TILESET = 0x2F5C14


def R(a, b):
    return list(range(a, b + 1))


def small(tiles, text, align='center', **kw):
    d = {'grid': [tiles], 'band': (0, 7), 'text': text, 'align': align}
    d.update(kw); return d


def big(top, bottom, text, **kw):
    # 장식 사이에 9px 글리프의 본획만 그린다.
    d = {'grid': [top, bottom], 'band': (5, 13), 'text': text, 'align': 'center',
         'font': 'Galmuri9', 'height': 9}
    d.update(kw); return d


LABELS = [
    # 서브 화면 라벨 (배경 A, 글자 3, 그림자 8)
    small(R(0x14, 0x19), '코드네임', 'left', colors=(0xa, 0x3, 0x8)),
    small(R(0x34, 0x39), 'E크리스탈', 'left', colors=(0xa, 0x3, 0x8)),
    small(R(0x54, 0x5A), '플레이 타임', 'left', colors=(0xa, 0x3, 0x8)),
    # 칭호 (오른쪽 맞춤: 화면에서 끝 칸이 고정)
    small(R(0x24B, 0x24F), '신', 'right', colors=(0x3, 0x1, 0x2)),
    small(R(0x250, 0x253), '마스터', 'right', colors=(0x3, 0x1, 0x2)),
    small(R(0x260, 0x263), '용사', 'right', colors=(0x3, 0x1, 0x2)),
    small(R(0x264, 0x267), '영웅', 'right', colors=(0x3, 0x1, 0x2)),
    small(R(0x268, 0x26E), '구세주', 'right', colors=(0x3, 0x1, 0x2)),
    small(R(0x26F, 0x270), '신', 'right', colors=(0x3, 0x1, 0x2)),
    small(R(0x271, 0x273), '질풍', 'right', colors=(0x3, 0x1, 0x2)),
    small(R(0x280, 0x284), '파괴신', 'right', colors=(0x3, 0x1, 0x2)),
    small(R(0x285, 0x289), '검호', 'right', colors=(0x3, 0x1, 0x2)),
    small(R(0x28A, 0x28F), '저격수', 'right', colors=(0x3, 0x1, 0x2)),
    small(R(0x290, 0x295), '엘프중독', 'right', colors=(0x3, 0x1, 0x2)),
    small(R(0x2A0, 0x2A3), '굼벵이', 'right', colors=(0x3, 0x1, 0x2)),
    small(R(0x2A4, 0x2AA), '평화주의', 'right', colors=(0x3, 0x1, 0x2)),
    small(R(0x2AB, 0x2AD), '전사', 'right', colors=(0x3, 0x1, 0x2)),
    small(R(0x2AE, 0x2B6), '태엽인형', 'right', colors=(0x3, 0x1, 0x2)),
    small(R(0x2C0, 0x2C4), '고철', 'right', colors=(0x3, 0x1, 0x2)),
    small(R(0x2C5, 0x2C7), '무능', 'right', colors=(0x3, 0x1, 0x2)),
    small(R(0x2C8, 0x2CC), '고물', 'right', colors=(0x3, 0x1, 0x2)),
    small(R(0x2E0, 0x2E4), '수집가', 'right', colors=(0x3, 0x1, 0x2)),
    small(R(0x2E5, 0x2E8), '패배자', 'right', colors=(0x3, 0x1, 0x2)),
    small(R(0x2E9, 0x2EC), '헌터', 'right', colors=(0x3, 0x1, 0x2)),
    # 옵션 화면 (배경 9, 글자 1, 그림자 8)
    small(R(0x206, 0x208), '타입', 'right', colors=(0x9, 0x1, 0x8)),
    small(R(0x209, 0x20C), '커스텀', colors=(0x9, 0x1, 0x8)),
    small(R(0x20D, 0x210), '대시', colors=(0x9, 0x1, 0x8)),
    small(R(0x211, 0x214), '점프', colors=(0x9, 0x1, 0x8)),
    small(R(0x220, 0x227), '메인 웨폰', colors=(0x9, 0x1, 0x8)),
    small(R(0x228, 0x22E), '서브 웨폰', colors=(0x9, 0x1, 0x8)),
    small(R(0x22F, 0x232), '버튼', 'left', colors=(0x9, 0x1, 0x8)),
    small(R(0x240, 0x243), '전환', colors=(0x9, 0x1, 0x8)),
    small(R(0x246, 0x247), '서브', colors=(0x9, 0x1, 0x8)),
    small(R(0x300, 0x306), '버튼 설정', 'left', pad=(1, 0), colors=(0x6, 0x5, 0x9)),
    small(R(0x307, 0x30D), '공격 모드', 'left', pad=(1, 0), colors=(0x9, 0x8, 0x9)),
    # 아래 단추 라벨
    big(R(0x163, 0x167), R(0x183, 0x187), '엘프목록', colors=(0xa, 0x3, 0xa)),
    big(R(0x171, 0x175), R(0x191, 0x195), '옵션', colors=(0xa, 0x3, 0xa)),
    big(R(0x1C1, 0x1C5), R(0x1E1, 0x1E5), '상태', colors=(0xa, 0x3, 0xa)),
    big(R(0x1D2, 0x1D6), R(0x1F2, 0x1F6), '엘프목록', colors=(0xa, 0x3, 0xa)),
    big(R(0x3C3, 0x3C7), R(0x3E3, 0x3E7), '옵션', colors=(0xa, 0x3, 0xa)),
    big(R(0x385, 0x389), R(0x3A5, 0x3A9), '상태', colors=(0xa, 0x3, 0xa)),
]


def title(grid, text, fill):
    return {'grid': grid, 'band': (0, 15), 'text': text, 'align': 'center',
            'colors': (0, fill, 11), 'font': 'Galmuri11', 'height': 11, 'dy': 2}


# 0x532C94부터 16타일씩 한 행. 각 스프라이트의 외곽선과 투명 영역을 보존한다.
WEAPON_LABELS = [
    {'grid': grid, 'band': (3, 12), 'text': text, 'align': 'center',
     'colors': (0, 1, 9), 'pad': (5, 5), 'font': 'Galmuri9', 'height': 9}
    for grid, text in [
        ([R(0, 4), R(16, 20)], '메인'),
        ([R(5, 9), R(21, 25)], '엘프'),
        ([R(27, 31), R(43, 47)], '서브'),
    ]
]

TITLE_LABELS = [
    (0x30A314, title([R(1, 22), R(23, 44)], '스타트 버튼을 눌러 주세요', 4)),
    (0x30AAD4, dict(title([R(1, 10), R(12, 21)], '처음부터', 1), dx=-9)),
    # 둘째 줄 마지막 칸은 빈 「처음부터」 타일을 재사용한다.
    (0x30AAD4, title([R(22, 29) + [None] * 2, R(30, 36) + [None] * 3], '이어서', 1)),
]

RESULT_LABELS = [
    dict(title([R(0x1D0, 0x1D5), R(0x1F0, 0x1F5)], '결과', 9),
         colors=(5, 9, 6), align='left', pad=(1, 0), bold=True),
    small(R(0x16, 0x1A), '미션', 'left', colors=(3, 1, 2)),
    small(R(0x36, 0x3B), '클리어 시간', 'left', colors=(3, 1, 2)),
    small(R(0x56, 0x5D), '처치 수', 'left', colors=(3, 1, 2)),
    small(R(0x76, 0x7B), '받은 피해', 'left', colors=(3, 1, 2)),
    small(R(0x96, 0x99), '재도전', 'left', colors=(3, 1, 2)),
    small(R(0xB6, 0xB8), '엘프', 'left', colors=(3, 1, 2)),
    small(R(0xD6, 0xD9), '합계', 'left', colors=(3, 1, 2)),
    small(R(0xF6, 0xF9), '레벨', 'left', colors=(3, 1, 2)),
    small(R(0x116, 0x11C), '코드네임', 'left', colors=(3, 1, 2)),
]


def apply(rom, source):
    """원본 타일에서 라벨을 만들고 허용된 픽셀만 빌드에 반영한다."""
    specs = [(TILESET, label) for label in LABELS]
    specs += [(0x532C94, label) for label in WEAPON_LABELS]
    specs += TITLE_LABELS
    specs += [(0x2FFC34, label) for label in RESULT_LABELS]
    writes = {}
    for base, label in specs:
        offsets = [base + tile * 32 for row in label['grid'] for tile in row if tile is not None]
        for offset in offsets:
            if offset in writes or offset < 0 or offset + 32 > len(source):
                raise ValueError(f"overlapping or invalid label tile at {offset:#x}")
            if rom[offset:offset + 32] != source[offset:offset + 32]:
                raise ValueError(f"label tile overlaps another build change at {offset:#x}")
            writes[offset] = None

    result = bytearray(source)
    for base, label in specs:
        before = gfxtext.canvas(source, base, label['grid'])
        gfxtext.draw_label(result, base, label)
        after = gfxtext.canvas(result, base, label['grid'])
        y0, y1 = label['band']
        left, right = label.get('pad', (0, 0))
        for y, row in enumerate(before):
            for x, pixel in enumerate(row):
                if (y < y0 or y > y1 or x < left or x >= len(row) - right) and after[y][x] != pixel:
                    raise ValueError(f"label {label['text']!r} changed protected pixels")
        if before == after:
            raise ValueError(f"label {label['text']!r} has no changes")

    # 「이어서」 타일맵이 「처음부터」의 오른쪽 빈 칸을 공유한다.
    for tile in (9, 10, 19, 20, 21):
        offset = 0x30AAD4 + tile * 32
        if any(result[offset:offset + 32]):
            raise ValueError(f"shared title tile {tile:#x} is no longer blank")

    for offset in writes:
        rom[offset:offset + 32] = result[offset:offset + 32]
    return len(specs)
