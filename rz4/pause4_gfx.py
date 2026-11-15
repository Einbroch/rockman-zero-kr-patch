"""4편 서브 화면(일시정지) 네 쪽의 BG 그림 글자 — 타일이 무압축이라 ROM 제자리에서 고친다.

쪽마다 BG1 타일이 ROM 의 연속 구간에서 VRAM 으로 올라간다(기준 = 타일 0 의 ROM 주소):
- 상태 쪽 0xB7A614, 칩 쪽 0xB784F4(타일 0x200~), 옵션 쪽 0xB805D4, 엘프 쪽 0xB804F4(0x200~)
위치는 일시정지 VRAM 을 scratch/z2g/labelgrid.py 로 되읽어 확정했다(칸 사각형 -> 기준·타일 격자, 바이트 대조).
그리기는 2편 pause2_gfx.draw. 사각형 밖 픽셀이 바뀌면 실패.
"""

from pause2_gfx import draw, label, ERASE

R = lambda a, b: list(range(a, b + 1))


def grid_bg(lo, hi, cross):
    """격자 무늬 배경: 8px 마다 세로·가로 줄(hi), 교차점(cross), 나머지 lo. 줄 위치는 x%8==3, y%8==3."""
    return lambda x, y: cross if x % 8 == 3 and y % 8 == 3 else hi if x % 8 == 3 or y % 8 == 3 else lo


TOP = (grid_bg(2, 3, 4), 0xB, 1, None)         # 상태 쪽 위 항목(プレイタイム 등)
BAR = (grid_bg(2, 5, 6), 0xF, 2, None)         # 아래 막대 L/R 쪽 이름(그림자는 배경색이라 그리지 않는 셈)
BOX = (grid_bg(8, 9, 0xA), 0, 0, None)       # L/R 단추의 「ボタン」 상자를 막대 배경으로 지운다(L·R 글자 상자만 남김)
TAB = (0xC, 0xF, 0xC, None)                    # 옵션 쪽 탭 제목
OPT = (grid_bg(1, 2, 2), 7, 9, None)           # 옵션 쪽 항목
ELF = (3, 0xE, 1, None)                        # 엘프 쪽 작은 라벨
SMALL = dict(font='Galmuri7', height=7)


def bar(left, right, ltext, rtext):
    """아래 막대 한 벌: 왼쪽 11칸(이름 x8~47, L 단추) + 오른쪽 11칸(R 단추, 이름 x40~80). 두 줄 타일."""
    return [
        label(left, (8, 4, 47, 12), ltext, BAR, font='Galmuri9', height=9, gap=0, bold=len(ltext) <= 3),
        label(left, (57, 7, 81, 13), ERASE, BOX),
        label(right, (16, 7, 37, 13), ERASE, BOX),
        label(right, (40, 4, 80, 12), rtext, BAR, font='Galmuri9', height=9, gap=0, bold=len(rtext) <= 3),
    ]


PAGES = {
    # 상태 쪽
    0xB7A614: [
        label([R(0x2E, 0x33)], (0, 0, 47, 7), '플레이 타임', TOP, align='left', **SMALL),
        label([[0x14] + R(0x35, 0x37) + [0x17, 0x18, 0x39]], (8, 0, 55, 7), 'E크리스탈', TOP, align='left', **SMALL),
        label([R(0x67, 0x6B)], (0, 0, 39, 7), '코드네임', TOP, align='left', **SMALL),
        *bar([R(0x84, 0x8C) + [0x8C, 0x8E], R(0xA4, 0xAE)],
             [[0x8F, 0x90, 0x8C, 0x8C] + R(0x92, 0x98), [0xAF, 0xB0, 0xB1, 0x91] + R(0xB2, 0xB8)],
             '엘프 세트', '칩 세트'),
    ],
    # 칩 쪽
    0xB784F4: [
        *bar([R(0x20B, 0x215), R(0x22B, 0x235)],
             [R(0x21B, 0x21F) + R(0x240, 0x245), R(0x23B, 0x23F) + R(0x260, 0x265)],
             '상태', '옵션'),
    ],
    # 옵션 쪽
    0xB805D4: [
        label([R(0x05, 0x0C), R(0x25, 0x2C)], (7, 5, 56, 11), '버튼 설정', TAB, **SMALL),
        label([R(0x140, 0x147), R(0x160, 0x167)], (7, 5, 56, 11), '공격 모드', TAB, **SMALL),
        label([R(0x0E, 0x15), R(0x2E, 0x35)], (7, 5, 56, 11), '커맨드 대시', TAB, **SMALL),
        label([R(0x80, 0x83)], (0, 0, 31, 7), '타입-', OPT, align='right', **SMALL),
        label([R(0x84, 0x87)], (0, 0, 31, 7), '커스텀', OPT, **SMALL),
        label([R(0x88, 0x8F)], (0, 0, 63, 7), '메인 무기', OPT, **SMALL),
        label([R(0x90, 0x93)], (0, 0, 31, 7), '점프', OPT, **SMALL),
        label([R(0x94, 0x97)], (0, 0, 31, 7), '대시', OPT, **SMALL),
        label([R(0x98, 0x9E)], (0, 0, 55, 7), '서브 무기', OPT, **SMALL),
        label([R(0xF9, 0xFB)], (0, 0, 23, 7), '버리기', OPT, **SMALL),
        label([R(0xA0, 0xA3)], (0, 0, 31, 7), '버튼', OPT, align='left', **SMALL),
        label([R(0xBC, 0xBF)], (0, 0, 31, 7), '셀렉트', OPT, align='right', **SMALL),
        label([[0xAC, 0xAD]], (0, 0, 15, 7), '켬', OPT, **SMALL),
        label([[0xAE, 0xAF]], (0, 0, 15, 7), '끔', OPT, **SMALL),
        *bar([R(0x1B, 0x1F) + R(0x40, 0x45), R(0x3B, 0x3F) + R(0x60, 0x65)],
             [R(0x4B, 0x55), R(0x6B, 0x75)],
             '칩 세트', '엘프 세트'),
    ],
    # 엘프 쪽
    0xB804F4: [
        label([R(0x2B6, 0x2BA)], (0, 0, 39, 7), '캐퍼시티', ELF, align='left', **SMALL),
        label([R(0x29D, 0x29F)], (0, 0, 23, 7), '레벨', ELF, **SMALL),     # 두 줄이 공유
        label([[0x2C0]], (0, 1, 0, 6), ERASE, ELF),                      # 옛 「ル」 꼬리
        label([[0x2C3]], (0, 1, 0, 6), ERASE, ELF),
        label([R(0x2BC, 0x2BE)], (0, 0, 23, 7), '토털', ELF, align='left', **SMALL),
        *bar([R(0x203, 0x20D), R(0x223, 0x22D)],
             [R(0x213, 0x21D), R(0x233, 0x23D)],
             '옵션', '상태'),
    ],
}


# 스프라이트 라벨(1D 배치, 무압축): 32x16 블록 = 타일 0~3 / 4~7. 기준은 그 블록 첫 타일의 ROM 주소.
SPR = (0, 4, 2, 1)
SPR_OPTS = dict(font='Galmuri9', height=9, bold=True)
BLOCK = [R(0, 3), R(4, 7)]
PAGES.update({
    0xC61748: [label(BLOCK, (4, 2, 31, 13), '메인', SPR, **SPR_OPTS)],
    0xC61D48: [label([[0], [1]], (0, 2, 7, 13), ERASE, SPR)],   # 메인 오른쪽 8x16 꼬리(옛 「ン」 끝)
    0xC61848: [label(BLOCK, (2, 2, 31, 13), '서브', SPR, **SPR_OPTS)],
    # 에스케이프: 32x16 블록 + 16x16(타일 8~11)
    0xC61B48: [label([R(0, 3) + [8, 9], R(4, 7) + [10, 11]], (1, 2, 45, 13), '탈출', SPR, **SPR_OPTS)],
    0xC6AC28: [label(BLOCK, (1, 2, 31, 13), '헤드', SPR, **SPR_OPTS)],
    0xC6B528: [label(BLOCK, (0, 2, 31, 13), '보디', SPR, **SPR_OPTS)],
    0xC6B628: [label(BLOCK, (1, 2, 31, 13), '풋', SPR, **SPR_OPTS)],
    # 부품 목록: 왼쪽 블록 0x360(타일 8~15) + 오른쪽 블록 0x358(0~7)
    0xC6B728: [label([R(8, 11) + R(0, 3), R(12, 15) + R(4, 7)], (1, 2, 62, 13), '부품 목록', SPR, **SPR_OPTS)],
})


# 타이틀 메뉴·난이도 단어(OBJ 시트 0xCAE368 = OBJ 타일 0x200, 무압축). 단어마다 어두운 판/밝은 판 32x16 블록.
# 16x16 조각(0x110 ト, 0x114 ら, 0x118 ド, 0x11C ム)은 여러 단어가 함께 쓰므로 지우고, 한글은 블록 안에만 그린다.
MENU_BASE = 0xCAE368
DARK, LIGHT = (0, 1, 4, 4), (0, 5, 8, 8)
BIG = dict(font='Galmuri11', height=11, bold=True)


def word(blocks, text, colors):
    top = sum((R(b, b + 3) for b in blocks), [])
    bottom = sum((R(b + 4, b + 7) for b in blocks), [])
    return label([top, bottom], (0, 1, 32 * len(blocks) - 1, 13), text, colors, **BIG)


def piece(p):
    return label([[p, p + 1], [p + 2, p + 3]], (0, 0, 15, 15), ERASE, DARK)


PAGES[MENU_BASE] = [
    word([0x08, 0x00], '처음부터', DARK), word([0x18, 0x10], '처음부터', LIGHT),
    word([0x28, 0x20], '이어서', DARK), word([0x38, 0x30], '이어서', LIGHT),
    word([0x50, 0x48, 0x40], '데이터베이스', DARK), word([0x68, 0x60, 0x58], '데이터베이스', LIGHT),
    word([0x78, 0x70], '이지', DARK), word([0x88, 0x80], '이지', LIGHT),
    word([0x98, 0x90], '노멀', DARK), word([0xA8, 0xA0], '노멀', LIGHT),
    word([0xB0], '하드', DARK), word([0xB8], '하드', LIGHT),
    word([0xD0, 0xC8, 0xC0], '얼티밋', DARK), word([0xE8, 0xE0, 0xD8], '얼티밋', LIGHT),
    word([0xF8, 0xF0], '미니 게임', DARK), word([0x108, 0x100], '미니 게임', LIGHT),
    piece(0x110), piece(0x114), piece(0x118), piece(0x11C),
]


# 결과 화면·저장 메뉴 등(옵션 쪽과 같은 타일셋 0xB805D4). 작은 항목은 옵션 항목 스타일, 큰 것은 글자마다 C 테두리.
CAP = (grid_bg(7, 8, 9), 0xF, 0xC, 0xC)
PAGES[0xB805D4] += [
    label([R(0x55, 0x5F), R(0x75, 0x7F)], (45, 2, 85, 10), '결과', CAP, **SMALL),
    label([R(0x180, 0x18E), R(0x1A0, 0x1AE)], (8, 2, 43, 10), '저장', CAP, **SMALL),
    label([R(0x180, 0x18E), R(0x1A0, 0x1AE)], (55, 2, 91, 10), '삭제', CAP, **SMALL),
    label([R(0x1C0, 0x1C7), R(0x1E0, 0x1E7)], (8, 2, 43, 10), '로드', CAP, **SMALL),
    label([R(0x193, 0x19B), R(0x1B3, 0x1BB)], (0, 4, 50, 12), '미니 게임', CAP, **SMALL),
    *[label([R(a, b)], (0, 0, (b - a + 1) * 8 - 1, 7), text, OPT, align='left', **SMALL) for a, b, text in (
        (0xC0, 0xC4, '미션'), (0xC5, 0xCA, '클리어 타임'), (0xCB, 0xD2, '처치 수'), (0xD3, 0xD8, '받은 피해'),
        (0xD9, 0xDC, '재도전'), (0xDD, 0xDF, '엘프'), (0xE3, 0xE6, '합계'), (0xE7, 0xED, '평균'),
        (0xEE, 0xF1, '레벨'), (0xF2, 0xF8, '코드네임'), (0x115, 0x119, '날씨'), (0x11A, 0x11D, '레벨'))],
]

# 코드네임(무압축, 0xB7E4F4 부터 64x8 칸 0x100 바이트씩). 마지막 0xB800F4 는 가운데 정렬 「センシ」.
CODE = (grid_bg(2, 3, 4), 0xE, 1, None)
CODENAMES = ['용사', '영웅', '구세주', '갓', '완벽주의', '배신의', '질풍의', '준족의', '느림보', '냉혈의',
             '상처 없는', '상처투성이', '불사신', '의존적인', '냉정한', '전사', '건맨', '슈터', '스나이퍼',
             '검사', '검객', '검성', '아이언 피스트', '블래스트 피스트', '마스터 피스트', '웨폰 마스터', '호쾌한']
for k, text in enumerate(CODENAMES):
    align = 'center' if 16 <= k <= 21 else 'left'   # 원문도 짧은 뒷말(ガンマン~ケンセイ)은 가운데 정렬
    PAGES[0xB7E4F4 + k * 0x100] = [label([R(0, 7)], (0, 0, 63, 6), text, CODE, align=align, **SMALL)]
PAGES[0xB800F4] = [label([R(0, 7)], (16, 0, 47, 6), '전사', CODE, **SMALL)]

# 결과 화면은 코드네임을 다른 사본에서 읽는다: 타일셋 0xB89EF4 의 타일 0x300 = 0xB8FEF4 부터 같은 배열·간격,
# 글자만 한 줄 아래(1~7행). 마지막 0xB91AF4 가 가운데 정렬 「センシ」.
for k, text in enumerate(CODENAMES):
    align = 'center' if 16 <= k <= 21 else 'left'
    PAGES[0xB8FEF4 + k * 0x100] = [label([R(0, 7)], (0, 0, 63, 7), text, CODE, align=align, dy=1, **SMALL)]
PAGES[0xB91AF4] = [label([R(0, 7)], (0, 0, 63, 7), '전사', CODE, dy=1, **SMALL)]   # 0행에 남는 원래 테두리까지 지운다

# 결과 화면 웨더 레벨 값(옵션 타일셋 0xB805D4): 0x120~0x125 「ツウジョウ」, 0x126~0x129 「カンタン」.
# 원문은 흰 글자(8)·남색 테두리(9)·옵션과 같은 격자 배경(1/2); 7px 한글은 8행에 테두리가 다 안 들어가 그림자로 대신한다.
VALUE = (grid_bg(1, 2, 2), 8, 9, None)
PAGES[0xB805D4] += [label([R(0x120, 0x125)], (0, 0, 47, 7), '보통', VALUE, align='left', **SMALL),
                    label([R(0x126, 0x129)], (0, 0, 31, 7), '쉬움', VALUE, align='left', **SMALL)]


def edit(rom, base, specs):
    """ROM 의 base 부터 타일 버퍼를 잘라 라벨을 그리고, 사각형 밖 픽셀이 그대로인지 확인한 뒤 되돌려 쓴다."""
    top = max(t for spec in specs for row in spec['grid'] for t in row) + 1
    original = bytes(rom[base:base + top * 32])
    buf = bytearray(original)
    allowed = set()
    for spec in specs:
        draw(buf, spec)
        x0, y0, x1, y1 = spec['rect']
        for r, row in enumerate(spec['grid']):
            for i, t in enumerate(row):
                allowed.update((t, y, x) for y in range(8) for x in range(8)
                               if x0 <= i * 8 + x <= x1 and y0 <= r * 8 + y <= y1)
    for t in range(top):
        for y in range(8):
            for x in range(8):
                index = t * 32 + y * 4 + x // 2
                if (t, y, x) not in allowed and (original[index] ^ buf[index]) >> (x & 1) * 4 & 15:
                    raise ValueError(f'protected pixel changed at {base:#x} tile {t:#x}')
    return bytes(buf)


def apply(rom, write):
    for base, specs in PAGES.items():
        new = edit(rom, base, specs)
        changed = [i for i in range(0, len(new), 32) if new[i:i + 32] != rom[base + i:base + i + 32]]
        for i in changed:
            write(base + i, new[i:i + 32], f'sub-screen tile {base:#x}+{i // 32:#x}')
