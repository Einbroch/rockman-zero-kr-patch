"""3편 서브 화면(일시정지) 네 쪽의 BG 그림 글자.

쪽마다 압축 타일셋 하나가 VRAM 0x4000 또는 0x8000 에 올라가고, 512px 폭 맵을 가로로 넘긴다.
- 0x547410 상태(ステータス), 0x547424 EX 스킬, 0x547438 옵션(+결과 화면), 0x54744C 엘프 목록
라벨 위치는 일시정지 중 VRAM 맵을 타일셋 번호로 되읽어 확정했다(scratch/z2g/mapdump.py).
그리기는 2편 pause2_gfx.draw 를 쓴다: 사각형 안을 배경색으로 지우고 글자를 다시 그린다.

L/R 단추 라벨은 네 쪽 모두 3타일 행 구조: 위 작은 「ボタン」(y 3~9), 아래 큰 글자(y 11~22,
글자 7·외곽선 1). 맨 윗줄에 들어가는 이웃 테두리 타일은 사각형 밖이라 바뀌지 않는다.
"""

import struct

import lz77
from pause2_gfx import R, big, draw, label, strip

SMALL = (3, 7, 1, None)       # 상태 쪽 항목·「ボタン」: 배경 3, 글자 7, 그림자 1
BIG = (3, 7, 1, None)         # L/R 큰 글자: 외곽선을 넣으면 9px 한글이 뭉개진다
OPTION = (2, 7, 1, None)      # 옵션 쪽 항목
TAB = (5, 0xB, 8, None)       # 옵션 쪽 탭 제목
EXTAB = (0xC, 0xF, 0xC, None)  # EX 스킬 쪽 제목 띠


def buttons(grid, text, side, **kw):
    """L/R 단추 라벨 한 벌: 작은 「버튼」 + 큰 쪽 이름."""
    small = (13, 3, 42, 9) if side == 'L' else (32, 3, 57, 9)
    large = (16, 11, 57, 22) if side == 'L' else (6, 11, 51, 22)
    return [label(grid, small, '버튼', SMALL),
            big(grid, large, text, BIG, font='Galmuri9', height=9, dy=1, **{'bold': True, **kw})]


def three(top, mid, bottom):
    return [top, mid, bottom]


TILESETS = {
    # 상태
    0x547410: [
        strip(0xA7, 0xAD, '플레이 타임', SMALL, rect=(0, 0, 47, 7)),
        strip(0xC7, 0xCD, 'E크리스탈', SMALL, rect=(8, 0, 49, 7)),
        strip(0xE7, 0xED, '코드네임', SMALL, rect=(0, 0, 40, 7)),
        *buttons(three(R(0xAE, 0xB3) + [0x6C, 0x97], R(0xCE, 0xD5), R(0xEE, 0xF5)), '엘프 목록', 'L', gap=0, bold=False),
        *buttons(three([0xA4, 0x6D] + R(0xB8, 0xBD), R(0xD6, 0xDD), R(0xF6, 0xFD)), 'EX 스킬', 'R'),
    ],
    # EX 스킬
    0x547424: [
        label([R(0x34, 0x3B)], (17, 1, 51, 7), 'EX 스킬', EXTAB),
        *buttons(three(R(0x40, 0x47), R(0x60, 0x67), R(0x80, 0x87)), '상태', 'L'),
        *buttons(three(R(0x48, 0x4F), R(0x68, 0x6F), R(0x88, 0x8F)), '옵션', 'R'),
    ],
    # 옵션
    0x547438: [
        label([R(0x30, 0x39), R(0x50, 0x59)], (14, 3, 66, 10), '버튼 설정', TAB),
        label([R(0x70, 0x79), R(0x90, 0x99)], (13, 3, 66, 10), '공격 모드', TAB),
        strip(0xA6, 0xA8, '타입', OPTION, 'right'),   # 뒤에 「-A」 타일이 붙는다
        strip(0xA9, 0xAC, '커스텀', OPTION, 'center'),
        strip(0xC0, 0xC7, '메인 무기', OPTION, 'center'),
        strip(0xC8, 0xCE, '서브 무기', OPTION, 'center'),
        strip(0xB1, 0xB4, '점프', OPTION, 'center'),
        strip(0xAD, 0xB0, '대시', OPTION, 'center'),
        strip(0xCF, 0xD2, '버튼', OPTION),   # 앞 타일의 B·A·L·R 에 붙인다
        *buttons(three(R(0x40, 0x45) + [0x04, 0x05], R(0x60, 0x67), R(0x80, 0x87)), 'EX 스킬', 'L'),
        *buttons(three([0x07, 0x08] + R(0x4A, 0x4F), R(0x68, 0x6F), R(0x88, 0x8F)), '엘프 목록', 'R', gap=0, bold=False),
    ],
    # 엘프 목록
    0x54744C: [
        *buttons(three(R(0x49, 0x4E) + [0x02, 0x03], R(0x69, 0x70), R(0x89, 0x90)), '옵션', 'L'),
        *buttons(three([0x12, 0x13] + R(0x53, 0x58), R(0x71, 0x78), R(0x91, 0x98)), '상태', 'R'),
    ],
}

# 스프라이트 라벨(1D 배치, OBJ 타일 0x27A~): 32x16 블록 + 오른쪽 8x16 꼬리. 짝은 글자 이음으로 확정.
# 꼬리 0x4C 는 서브·フット 공용 빈 끝 조각이라 건드리지 않는다.
SPR = (0, 4, 2, 1)


def block(o, tail=None, left=None):
    top = R(o, o + 3) + ([tail] if tail is not None else [])
    bottom = R(o + 4, o + 7) + ([tail + 1] if tail is not None else [])
    if left is not None:
        top, bottom = [left] + top, [left + 1] + bottom
    return [top, bottom]


SPR_OPTS = dict(font='Galmuri9', height=9, bold=True)
TILESETS[0x5D7A24] = [
    label(block(0x00, 0x52), (2, 2, 37, 13), '메인', SPR, **SPR_OPTS),
    label(block(0x08), (2, 2, 31, 13), '서브', SPR, **SPR_OPTS),
    label(block(0x10, 0x56), (2, 2, 37, 13), '헤드', SPR, **SPR_OPTS),
    label(block(0x18, 0x58), (2, 2, 37, 13), '보디', SPR, **SPR_OPTS),
    label(block(0x20), (2, 2, 31, 13), '풋', SPR, **SPR_OPTS),
    label(block(0x28, 0x5E), (2, 2, 37, 13), '서브탱크', SPR, font='Galmuri7', height=7, dy=1),
    # 에스케이프: 왼쪽 8x16(0x60) + 블록 0x30 + 오른쪽 16x16(0x44)
    label([[0x60] + R(0x30, 0x33) + [0x44, 0x45], [0x61] + R(0x34, 0x37) + [0x46, 0x47]],
          (7, 2, 49, 13), '탈출', SPR, **SPR_OPTS),
]

# 엘프 목록 단추(0x5FD564, OBJ 0x36F~): 단추 k = 왼쪽 블록 2k+1 + 오른쪽 블록 2k (각 32x16)
ELF = (2, 9, 1, 1)


def button(k):
    left, right = 8 * (2 * k + 1), 8 * (2 * k)
    return [R(left, left + 3) + R(right, right + 3), R(left + 4, left + 7) + R(right + 4, right + 7)]


TILESETS[0x5D7F60] = [
    label(button(0), (3, 2, 60, 13), '새틀라이트 1', ELF, font='Galmuri9', height=9, gap=0),
    label(button(1), (3, 2, 60, 13), '새틀라이트 2', ELF, font='Galmuri9', height=9, gap=0),
    label(button(2), (7, 2, 58, 13), '퓨전', ELF, **SPR_OPTS),
    label(button(3), (7, 2, 58, 13), 'E크리스탈', ELF, **SPR_OPTS),
    label(button(4), (7, 2, 58, 13), '목록', ELF, **SPR_OPTS),
]

# 미션 결과 화면(옵션과 같은 타일셋 0x547438). 낱말마다 연속 타일, 탁점은 따로 한 칸.
TILESETS[0x547438] += [
    label([R(0xE0, 0xEA), R(0x100, 0x10A)], (11, 3, 68, 10), '결과', TAB),
    label([R(0xF3, 0xFD), R(0x113, 0x11D)], (11, 3, 68, 10), '미니 게임', TAB),
    label([R(0x1D2, 0x1DE)], (16, 0, 87, 7), '시크릿 디스크', TAB),
    strip(0x120, 0x124, '미션', OPTION),
    strip(0x125, 0x12A, '클리어 타임', OPTION),
    strip(0x12B, 0x132, '처치 수', OPTION),
    strip(0x133, 0x138, '받은 피해', OPTION),
    strip(0x139, 0x13C, '재도전', OPTION),
    strip(0x13D, 0x13F, '엘프', OPTION),
    strip(0x143, 0x146, '합계', OPTION),
    strip(0x147, 0x14D, '평균', OPTION),
    strip(0x14E, 0x151, '레벨', OPTION),
    strip(0x152, 0x158, '코드네임', OPTION),
]

# 코드네임(0x5475DC): 64x8 칸 32개, 타일 행마다 4칸. 「〜の」 앞말과 뒷말이 따로 있다(15번은 빈칸).
CODENAMES = [
    '용사', '영웅', '구세주', '갓',
    '완벽주의', '배신의', '질풍의', '준족의',
    '느림보', '냉혈의', '상처 없는', '상처투성이',
    '불사신', '디스크', '엘프', None,
    '건맨', '슈터', '스나이퍼', '검사',
    '검객', '검성', '스태버', '페네트레이터',
    '로드 마스터', '리퍼', '슬래셔', '실드 마스터',
    '전사', '컬렉터', '킬러', '브리더',
]
TILESETS[0x5475DC] = [
    strip(n // 4 * 32 + n % 4 * 8, n // 4 * 32 + n % 4 * 8 + 7, text, OPTION)
    for n, text in enumerate(CODENAMES) if text
]

TARGETS = {0x547410: 0xF90000, 0x547424: 0xF94000, 0x547438: 0xF98000, 0x54744C: 0xF9C000,
           0x5D7A24: 0xFA0000, 0x5D7F60: 0xFA2000, 0x5475DC: 0xFA4000}
GAMEOVER_DESCRIPTOR, GAMEOVER_TARGET = 0x547A78, 0xFA8000


def apply_gameover(source, write):
    """게임오버 띠는 2편과 같은 구조(타일 0x0B~0x1C·0x2B~0x3C, 0x1540바이트)라 2편 함수를 쓴다."""
    import pause2_gfx
    saved = pause2_gfx.GAMEOVER_DESCRIPTOR
    pause2_gfx.GAMEOVER_DESCRIPTOR = GAMEOVER_DESCRIPTOR
    try:
        _, assets, size, layout = pause2_gfx.edit_gameover(source)
    finally:
        pause2_gfx.GAMEOVER_DESCRIPTOR = saved
    packed = lz77.compress(assets)
    if lz77.decompress(packed)[0] != assets:
        raise ValueError('RZ3 game over tileset failed readback')
    write(GAMEOVER_TARGET, packed, 'RZ3 game over tileset')
    write(GAMEOVER_DESCRIPTOR, struct.pack('<III', GAMEOVER_TARGET - GAMEOVER_DESCRIPTOR, len(packed), layout),
          'RZ3 game over descriptor')


def edit(source, descriptor, specs):
    """타일셋을 풀어 라벨을 그리고, 사각형 밖 픽셀이 그대로인지 확인한다."""
    relative, size, layout = struct.unpack_from('<III', source, descriptor)
    original, consumed = lz77.decompress(source, descriptor + relative)
    if not 0 < consumed <= size & 0x3FFFFF:
        raise ValueError(f'unexpected tileset size at {descriptor:#x}')
    assets = bytearray(original)
    allowed = set()
    for spec in specs:
        draw(assets, spec)
        x0, y0, x1, y1 = spec['rect']
        for r, row in enumerate(spec['grid']):
            for i, t in enumerate(row):
                allowed.update((t, y, x) for y in range(8) for x in range(8)
                               if x0 <= i * 8 + x <= x1 and y0 <= r * 8 + y <= y1)
    for t in range(len(original) // 32):
        for y in range(8):
            for x in range(8):
                index = t * 32 + y * 4 + x // 2
                if (t, y, x) not in allowed and (original[index] ^ assets[index]) >> (x & 1) * 4 & 15:
                    raise ValueError(f'protected pixel changed in {descriptor:#x} tile {t:#x}')
    return bytes(assets), size, layout


def apply(source, write, tilesets=None, targets=None):
    for descriptor, specs in (tilesets or TILESETS).items():
        target = (targets or TARGETS)[descriptor]
        assets, size, layout = edit(source, descriptor, specs)
        packed = lz77.compress(assets)
        if lz77.decompress(packed)[0] != assets or len(packed) > 0x4000:
            raise ValueError(f'RZ3 sub-screen tileset {descriptor:#x} failed readback')
        write(target, packed, f'RZ3 sub-screen tileset {descriptor:#x}')
        write(descriptor, struct.pack('<III', target - descriptor, (size & ~0x3FFFFF) | len(packed), layout),
              f'RZ3 sub-screen descriptor {descriptor:#x}')
    if tilesets is None:
        apply_gameover(source, write)
