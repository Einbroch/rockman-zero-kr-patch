"""Galmuri11 BDF -> 록맨 제로 VWF 글리프 (4bpp, 높이 16, 폭 4의 배수).

글리프 한 장 = 폭 W(4/8/12) x 16, 4bpp 행 우선, 한 행 W/2 바이트.
조각(quantum) = 4px 열 = 행마다 2바이트 -> 조각 하나 = 16행 x 2바이트 = 32바이트.
저장 형식: 글리프는 조각 단위로 연속 저장 (조각 q 는 글리프 시작 + q*32).
"""
import re

COLOR = 1          # 본획 색 (일본판 폰트와 같음)
TOP = 2            # 일본판 글리프 잉크 시작 행
ASCENT = 14        # Galmuri11 FONT_ASCENT


def load_bdf(path):
    t = open(path, encoding='utf-8', errors='replace').read()
    glyphs = {}
    for blk in t.split('STARTCHAR ')[1:]:
        m = re.search(r'ENCODING (-?\d+)', blk)
        if not m:
            continue
        cp = int(m[1])
        dw = int(re.search(r'DWIDTH (\d+)', blk)[1])
        w, h, xo, yo = map(int, re.search(r'BBX (-?\d+) (-?\d+) (-?\d+) (-?\d+)', blk).groups())
        bm = blk.split('BITMAP\n', 1)[1].split('ENDCHAR')[0].split()
        rows = [int(r, 16) for r in bm]
        glyphs[cp] = (dw, w, h, xo, yo, rows, len(bm[0]) * 4 if bm else 0)
    return glyphs


def render(glyphs, ch, cell_w=None):
    """문자 -> (폭, 16행 x 폭 픽셀 배열). 폭은 4의 배수로 올림."""
    cp = ord(ch)
    dw, w, h, xo, yo, rows, bits = glyphs[cp]
    W = cell_w if cell_w else max(4, (dw + 3) // 4 * 4)
    px = [[0] * W for _ in range(16)]
    # 기준선: 셀 행 TOP + (ASCENT - 3) 근처. Galmuri11 한글 BBX yo=0, h=11 -> 행 TOP..TOP+10
    base = TOP + 11  # 기준선 행 (잉크 아래 끝 다음 행)
    for r, bitsrow in enumerate(rows):
        y = base - yo - h + r
        for x in range(w):
            if bitsrow >> (bits - 1 - x) & 1:
                X = x + xo
                if 0 <= X < W and 0 <= y < 16:
                    px[y][X] = COLOR
    if A_STUB_TALL and is_a_family(ch):
        px = tall_a_stub(px)
    return W, px


# ㅏ 꼭지 굵히기(11/18 사용자 요청): 갈무리11 의 ㅏ·ㅘ 꼭지는 1px 점이라 스위치 컬렉션의 확대·쌍선형 화면에서 ㅣ 로 읽힌다.
# 꼭지 아래에 1px 을 더해 2px 높이로 만든다(옆으로 늘리면 다음 글자 첫 획에 붙는다).
A_STUB_TALL = True


def is_a_family(ch):
    o = ord(ch) - 0xAC00
    return 0 <= o < 11172 and (o // 28) % 21 in (0, 9)   # 중성 ㅏ·ㅘ


def find_a_stub(px):
    """오른쪽 세로획 x 와 꼭지 행 (꼭지 = 세로획 오른쪽 한 칸, 그 오른쪽은 빈 칸). 못 찾으면 None"""
    H, W = len(px), len(px[0])
    cols = [x for x in range(W) if sum(1 for y in range(H) if px[y][x]) >= 5]
    if not cols:
        return None
    xs = max(cols)
    rows = [y for y in range(H) if px[y][xs] and xs + 1 < W and px[y][xs + 1]
            and not (xs + 2 < W and px[y][xs + 2])]
    return (xs, rows[0]) if len(rows) == 1 else None


def tall_a_stub(px):
    hit = find_a_stub(px)
    if hit is None:
        raise ValueError('ㅏ 꼭지를 찾지 못함')
    xs, r = hit
    if not px[r + 1][xs] or px[r + 1][xs + 1]:
        raise ValueError('ㅏ 꼭지 아래에 세로획이 없음')
    px = [row[:] for row in px]
    px[r + 1][xs + 1] = px[r][xs + 1]
    return px


def to_quanta(W, px):
    """픽셀 -> 조각 바이트(조각마다 32바이트)."""
    out = bytearray()
    for q in range(W // 4):
        for y in range(16):
            row = px[y][q * 4:q * 4 + 4]
            out.append(row[0] | row[1] << 4)
            out.append(row[2] | row[3] << 4)
    return bytes(out)
