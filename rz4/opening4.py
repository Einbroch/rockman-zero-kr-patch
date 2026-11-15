"""4편 오프닝 문단(「レプリロイド…」 ~ 「キャラバンなのだから…」) 한글화.

글자가 아니라 그림이다. 문단 6개가 각각
  - 타일 묶음: 20바이트 서술자(팔레트 자기상대, 0x20, 타일 자기상대, 타일 크기, 플래그) 0xB6CD04 + 20*k
  - 맵: 0xB67908 + 0x788*k, 머리 (1, 1, 30, 32) 뒤 30x32 무압축 (세로로 흐르는 고리 버퍼)
로 되어 있다. 줄은 16px(맵 두 행) 높이, 가운데 정렬, 색은 팔레트 0~13 의 밝기 단계(0 = 투명).
원래 줄이 있던 두 행 자리에 같은 순서로 한국어 줄을 다시 그린다(줄 수·위치·타이밍 그대로).
타일이 원본보다 많아지면 빈 조각으로 옮기고 서술자를 고친다.
"""

import os
import struct

from PIL import Image, ImageDraw, ImageFont

DESCS = [0xB6CD04 + 20 * k for k in range(6)]
MAPS = [0xB67908 + 0x788 * k for k in range(6)]
COLS, ROWS = 30, 32
FONT = os.path.join(os.environ.get('WINDIR', 'C:/Windows'), 'Fonts', 'malgunbd.ttf')
SIZE = 12
LEVELS = 13                       # 팔레트 1~13 = 어두운 -> 밝은
SPARE = [(0xC19EA4, 0x215C), (0xCD6F68, 0x2098), (0xC424A4, 0x1B5C)]   # 0x4000 경계로 끝나는 0xFF 패딩(넘칠 때만)
MAX_TILES = 332                   # VRAM 문자 기준점 0x8000 에서 원본 최대치(0x2980)를 넘지 않는다

LINES = [
    # 1 (주황)
    ['레플리로이드…', '그것은 아득한 옛날에 만들어진', '한없이 인간에 가까운', '로봇…'],
    # 2
    ['고도의 기술로', '인격을 부여받은', '그들 레플리로이드는', '인간을 위해 일하고',
     '인간과 함께 걷는', '최고의 파트너가', '될 터였다…',
     '하지만…', '평화롭게 흐르는 시간의 이면에서', '인간과 레플리로이드의 톱니바퀴는',
     '조용히', '삐걱대기 시작한다…'],
    # 3
    ['한없이', '인간에 가깝기에', '레플리로이드는 때로', '인간을 거스르기까지 한다',
     '그러한', '위험한 레플리로이드를', '인간은 이레귤러라 부르며', '두려워했다…',
     '이레귤러가 된 레플리로이드는', '같은 레플리로이드의 손으로', '처분된다…',
     '그것이 인간이 이끌어 낸'],
    # 4
    ['해답이었다…',
     '주인인 인간을 지키려는', '레플리로이드들에게', '선택의 여지는 없다',
     '이리하여 언제 끝날지 모를', '레플리로이드끼리의', '격렬한 싸움이 시작된 것이다…',
     '수많은 싸움을 거듭하며…'],
    # 5
    ['시간이 흘러…', '레플리로이드가 지키는', '인간의 이상향', '네오 아르카디아가',
     '세워진 뒤에도', '싸움은 끝나지 않았다…',
     '자유를 바라는 이레귤러에 의해', '네오 아르카디아의', '지도자는 쓰러지고',
     '그리고 지금…', '네오 아르카디아였던 땅은', '범죄자인', '닥터 바일에게',
     '지배당하고 있다'],
    # 6
    ['인간의 이상향은', '이제 그림자조차 찾아볼 수 없고', '안전하다 할 만한 곳은 사라져',
     '그 땅을 떠나는 사람도', '적지 않다…',
     '그래…', '우리도 또한…', '바일의 지배에서 도망쳐 온', '캐러밴이니까…'],
]


def line_rows(rom, m):
    """원본 맵에서 줄(내용이 있는 두 행)의 시작 행 목록."""
    rows = [any(struct.unpack_from('<H', rom, m + 8 + (r * COLS + c) * 2)[0] & 0x3FF for c in range(COLS))
            for r in range(ROWS)]
    out, r = [], 0
    while r < ROWS:
        if rows[r]:
            if r % 2 or r + 1 >= ROWS or not rows[r + 1]:
                raise ValueError(f'opening line not on a 2-row pair at row {r}')
            out.append(r)
            r += 2
        else:
            r += 1
    return out


def render(text, font):
    """240x16 밝기 단계(0~13) 비트맵. 가운데 정렬, 글자 몸은 2~14px."""
    im = Image.new('L', (240, 16))
    d = ImageDraw.Draw(im)
    w = d.textlength(text, font=font)
    if w > 232:
        raise ValueError(f'opening line too wide ({w:.0f}px): {text}')
    d.text(((240 - w) / 2, 8), text, font=font, fill=255, anchor='lm')
    px = im.load()
    return [[min(LEVELS, round(px[x, y] * LEVELS / 255)) for x in range(240)] for y in range(16)]


def tile_bytes(bm, x0, y0):
    out = bytearray(32)
    for y in range(8):
        for x in range(8):
            out[y * 4 + x // 2] |= bm[y0 + y][x0 + x] << (4 * (x & 1))
    return bytes(out)


def apply(rom, write):
    font = ImageFont.truetype(FONT, SIZE)
    spare = list(SPARE)
    report = []
    for k, (desc, m) in enumerate(zip(DESCS, MAPS)):
        if struct.unpack_from('<4H', rom, m) != (1, 1, COLS, ROWS):
            raise ValueError(f'unexpected opening map header at {m:#x}')
        prel, psize, trel, tsize, flags = struct.unpack_from('<5I', rom, desc)
        tiles_at = desc + 8 + trel
        old_n = (tsize & 0xFFFFFF) // 32
        rows = line_rows(rom, m)
        if len(rows) != len(LINES[k]):
            raise ValueError(f'opening paragraph {k}: {len(rows)} lines, {len(LINES[k])} translations')
        tiles = [bytes(32)]
        index = {tiles[0]: 0}
        entries = [0] * (COLS * ROWS)
        for r, text in zip(rows, LINES[k]):
            bm = render(text, font)
            for half in (0, 1):
                for c in range(COLS):
                    data = tile_bytes(bm, c * 8, half * 8)
                    if data not in index:
                        index[data] = len(tiles)
                        tiles.append(data)
                    entries[(r + half) * COLS + c] = index[data]
        n = len(tiles)
        if n > MAX_TILES:
            raise ValueError(f'opening paragraph {k}: {n} tiles > {MAX_TILES}')
        blob = b''.join(tiles)
        write(m + 8, b''.join(struct.pack('<H', e) for e in entries), f'opening map {k}')
        if n <= old_n:
            write(tiles_at, blob + bytes(old_n * 32 - len(blob)), f'opening tiles {k}')
        else:
            for i, (a, room) in enumerate(spare):
                if room >= len(blob):
                    break
            else:
                raise ValueError(f'opening paragraph {k}: no free area for {n} tiles')
            if set(rom[a:a + len(blob)]) != {0xFF}:
                raise ValueError(f'opening spare area {a:#x} is not free')
            spare[i] = (a + len(blob), room - len(blob))
            write(a, blob, f'opening tiles {k} (moved)')
            write(desc + 8, struct.pack('<II', a - (desc + 8), (tsize & ~0xFFFFFF) | len(blob)),
                  f'opening tile descriptor {k}')
        report.append((k, old_n, n))
    return report
