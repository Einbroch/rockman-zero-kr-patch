"""타이틀 로고용 큰 한글 4자(18px 높이)를 직사각형 획으로 설계한다."""
H = 18

def blank(w): return [[0] * w for _ in range(H)]

def rect(g, x0, y0, x1, y1):
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            g[y][x] = 1

def rieul(g, x0, x1, y0, gap=1, s=2):
    """ㄹ: 가로 세 줄 + 오른쪽 위·왼쪽 아래 세로. 높이 = 3s + 2gap ... 실제 행 반환"""
    t = y0
    rect(g, x0, t, x1, t + s - 1); m = t + s + gap
    rect(g, x1 - s + 1, t, x1, m + s - 1)
    rect(g, x0, m, x1, m + s - 1); b = m + s + gap
    rect(g, x0, m, x0 + s - 1, b + s - 1)
    rect(g, x0, b, x1, b + s - 1)
    return b + s - 1

def rok():
    g = blank(22)
    end = rieul(g, 2, 18, 0, gap=1, s=2)            # 0..7
    rect(g, 9, end + 1, 11, end + 2)                 # ㅗ 기둥 8..9
    rect(g, 0, end + 3, 21, end + 5)                 # ㅗ 가로 10..12
    rect(g, 2, 14, 18, 15)                           # ㄱ 가로
    rect(g, 16, 14, 18, 17)                          # ㄱ 세로
    return g

def maen():
    g = blank(22)
    rect(g, 0, 0, 10, 2); rect(g, 0, 0, 2, 11); rect(g, 8, 0, 10, 11); rect(g, 0, 9, 10, 11)   # ㅁ
    rect(g, 13, 0, 15, 12); rect(g, 16, 5, 17, 6); rect(g, 19, 0, 21, 12)                    # ㅐ
    rect(g, 2, 13, 4, 17); rect(g, 2, 15, 21, 17)                                            # ㄴ
    return g

def je():
    g = blank(22)
    rect(g, 0, 1, 11, 3)                              # ㅈ 가로
    for k in range(11):                               # ㅈ 두 다리
        y = 4 + k
        rect(g, max(0, 5 - k // 2 * 1 - k // 2), y, max(0, 5 - k) + 2 if 5 - k >= 0 else 2, y) if False else None
    for k in range(12):
        y = 4 + k
        lx = 5 - (k * 5) // 11; rx = 6 + (k * 5) // 11
        rect(g, max(0, lx - 1), y, lx + 1, y)
        rect(g, rx - 1, y, min(11, rx + 1), y)
    rect(g, 13, 7, 15, 9)                             # ㅔ 왼쪽 짧은 가로
    rect(g, 15, 0, 17, 17); rect(g, 19, 0, 21, 17)    # ㅔ 세로 둘
    return g

def ro():
    g = blank(22)
    end = rieul(g, 2, 19, 0, gap=2, s=2)             # 0..9 (ㄹ)
    rect(g, 9, end + 1, 11, end + 5)                 # ㅗ 기둥
    rect(g, 0, end + 6, 21, min(H - 1, end + 8))     # ㅗ 가로
    return g

def word(glyphs, spacing):
    out = [[] for _ in range(H)]
    for k, g in enumerate(glyphs):
        for y in range(H):
            out[y] += g[y] + ([0] * spacing if k < len(glyphs) - 1 else [])
    return out

if __name__ == '__main__':
    for g in (rok(), maen(), je(), ro()):
        for row in g: print(''.join('#' if v else '.' for v in row))
        print()
