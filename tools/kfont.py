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
    return W, px


def to_quanta(W, px):
    """픽셀 -> 조각 바이트(조각마다 32바이트)."""
    out = bytearray()
    for q in range(W // 4):
        for y in range(16):
            row = px[y][q * 4:q * 4 + 4]
            out.append(row[0] | row[1] << 4)
            out.append(row[2] | row[3] << 4)
    return bytes(out)
