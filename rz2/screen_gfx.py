"""Korean labels in the compressed sub-screen and options tileset."""

import struct

import gfxtext
import lz77
import logo_rz2


TILESET = 0x392D6C
TILESET_DESCRIPTOR = 0x391850
COMPRESSED_CAPACITY = 0x24E0


def strip(first, last, text, colors, align='left'):
    return dict(grid=[list(range(first, last + 1))], text=text, colors=colors, align=align)


def button(first, text):
    return dict(
        grid=[list(range(first, first + 5)), list(range(first + 0x20, first + 0x25))],
        band=(2, 11), text=text, colors=(10, 3, 10), font='Galmuri9', height=9, dy=1,
    )


GOLD = (10, 3, 8)
MENU = (9, 1, 8)
CODENAME = (3, 1, 2)
CODENAMES = {
    0: '완벽주의', 1: '반역의', 2: '질풍의', 3: '느림보',
    4: '비정한', 5: '무결점의', 6: '상처투성이', 7: '불사의', 8: '엘프',
    10: '용사', 11: '영웅', 12: '구세주', 13: '신',
    14: '건맨', 15: '슈터', 16: '저격수', 17: '검사', 18: '검객', 19: '검성',
    20: '체인맨', 21: '체인 댄서', 22: '체인 마스터', 23: '리퍼',
    24: '슬래셔', 25: '실드 마스터', 26: '전사', 27: '킬러',
    28: '수집가', 29: '브리더', 30: '마스터',
}
LABELS = (
    strip(0x016, 0x01B, '코드네임', GOLD),
    strip(0x01C, 0x01F, CODENAMES[26], CODENAME, 'right'),
    strip(0x036, 0x03B, 'E크리스탈', GOLD),
    strip(0x056, 0x05C, '플레이 타임', GOLD),
    button(0x1D8, '옵션'),
    button(0x3C3, '상태'),
    strip(0x206, 0x208, '타입', MENU, 'right'),
    strip(0x209, 0x20C, '커스텀', MENU, 'center'),
    strip(0x20D, 0x210, '대시', MENU, 'center'),
    strip(0x211, 0x214, '점프', MENU, 'center'),
    strip(0x220, 0x227, '메인 무기', MENU, 'center'),
    strip(0x228, 0x22E, '서브 무기', MENU, 'center'),
    strip(0x22F, 0x232, '버튼', MENU),
    strip(0x240, 0x243, '전환', MENU, 'center'),
    strip(0x246, 0x247, '서브', MENU, 'center'),
    strip(0x249, 0x24F, '버튼 설정', (6, 5, 6)),
    strip(0x250, 0x256, '공격 모드', (9, 8, 9)),
)


def apply_codenames(source, write):
    # The alternate status layout uses 31 eight-tile cells in palette 0.
    # Its suffix renderer reads seven tiles, so the last tile is padding.
    descriptor = 0x391ECC
    offset, size, layout = struct.unpack_from('<III', source, descriptor)
    address = descriptor + offset
    if address != 0x403AA8 or size != 0xC0000864:
        raise ValueError('unexpected codename graphics descriptor')
    original, consumed = lz77.decompress(source, address)
    if len(original) != 0x2000 or consumed != size & 0x3FFFFF:
        raise ValueError('unexpected codename graphics dimensions')
    assets = bytearray(original)
    editable = set()
    for index, wording in CODENAMES.items():
        first = index * 8
        is_suffix = index >= 10
        last = first + (6 if is_suffix else 7)
        label = strip(first, last, wording, CODENAME, 'right' if is_suffix else 'left')
        before = gfxtext.canvas(original, 0, label['grid'])
        if set(pixel for row in before for pixel in row) - set(CODENAME):
            raise ValueError(f'unexpected colors for codename {index}')
        gfxtext.draw_label(assets, 0, label)
        editable.update(range(first * 32, (last + 1) * 32))

    if any(before != after and index not in editable
           for index, (before, after) in enumerate(zip(original, assets, strict=True))):
        raise ValueError('protected codename graphics changed')

    packed = lz77.compress(bytes(assets))
    if lz77.decompress(packed)[0] != assets:
        raise ValueError('codename graphics failed decompression readback')
    target = 0xF2C000
    write(target, packed, 'codename graphics')
    write(descriptor, struct.pack('<III', target - descriptor, (size & ~0x3FFFFF) | len(packed), layout),
          'codename graphics descriptor')


def apply_weapon_labels(source, write):
    descriptor = 0x433228
    offset, flags = struct.unpack_from('<II', source, descriptor)
    if descriptor + offset != 0x467F8C or flags != 0xA00007E0:
        raise ValueError('unexpected weapon label sprite descriptor')
    cursor = descriptor + offset
    rows = []
    for _ in range(5):
        header, = struct.unpack_from('<I', source, cursor)
        length = header & 0x7FFFFFFF
        chunk = source[cursor + 4:cursor + length]
        row = lz77.decompress(chunk)[0] if header >> 31 else chunk
        if len(row) != 0x200:
            raise ValueError('unexpected weapon label sprite row')
        rows.append(row)
        cursor += length
    if cursor != descriptor + offset + (flags & 0x3FFFFF):
        raise ValueError('weapon label sprite chunk bounds changed')

    original = b''.join(rows)
    sprites = bytearray(original)
    for top, labels in ((0, ('실드', '메인', '엘프')), (32, ('서브', '폼', 'EX기술'))):
        for column, label in zip((0, 5, 10), labels):
            first = top + column
            grid = [list(range(first, first + 5)), list(range(first + 16, first + 21))]
            # The original frame stays outside this inner rectangle.
            gfxtext.draw_label(sprites, 0, dict(
                grid=grid, band=(3, 12), pad=(5, 5), text=label,
                colors=(0, 15, 1), font='Galmuri9', height=9, gap=0,
            ))

    for y in range(32):
        grid_row = (y // 16) * 32 + ((y % 16) // 8) * 16
        for x in range(128):
            if 3 <= y % 16 <= 12 and x < 120 and 5 <= x % 40 < 35:
                continue
            tile = grid_row + x // 8
            index = tile * 32 + (y % 8) * 4 + x % 8 // 2
            shift = (x % 2) * 4
            if ((sprites[index] ^ original[index]) >> shift) & 15:
                raise ValueError('protected weapon sprite pixel changed')
    stream = bytearray()
    for start in range(0, 0x800, 0x200):
        row = bytes(sprites[start:start + 0x200])
        compressed = lz77.compress(row)
        if lz77.decompress(compressed)[0] != row:
            raise ValueError('weapon label row failed decompression readback')
        stream.extend(struct.pack('<I', 0x80000000 | (len(compressed) + 4)))
        stream.extend(compressed)
    stream.extend(source[cursor - 0x204:cursor])
    target = 0xF18000
    write(target, stream, 'weapon label sprites')
    write(descriptor, struct.pack('<II', target - descriptor, (flags & ~0x3FFFFF) | len(stream)),
          'weapon label sprite descriptor')


def apply_title_prompt(source, write):
    descriptor, address = 0x391EA4, 0x400F0C
    relative, size, layout = struct.unpack_from('<III', source, descriptor)
    if descriptor + relative != address or size != 0x2A7C:
        raise ValueError('unexpected title prompt descriptor')
    original, consumed = lz77.decompress(source, address)
    if len(original) != 0x4F00 or consumed > size:
        raise ValueError('unexpected title graphics dimensions')
    width, height = 176, 16
    start = 0x43C0
    end = start + width * height
    if set(original[start:end]) - {0, *range(0x72, 0x80)}:
        raise ValueError('unexpected title prompt colors')
    text_width, ink = gfxtext.text_bitmap('스타트를 눌러 주세요', 'Galmuri11', height=11)
    left = (width - text_width) // 2
    if left < 1:
        raise ValueError('title prompt does not fit')
    pixels = [[0] * width for _ in range(height)]
    for y, row in enumerate(ink, 2):
        for x, value in enumerate(row, left):
            if value:
                pixels[y][x] = 0x74
                pixels[y + 1][x + 1] = 0x7B
    for y, row in enumerate(ink, 2):
        for x, value in enumerate(row, left):
            if value:
                pixels[y][x] = 0x74
    tiles = bytes(
        color for top in (0, 8) for x in range(0, width, 8)
        for row in pixels[top:top + 8] for color in row[x:x + 8]
    )
    raw = original[:start] + tiles + original[end:]
    raw = logo_rz2.apply(raw, source)   # 「록맨®제로」 로고 (같은 타일셋)
    packed = lz77.compress(raw)
    if lz77.decompress(packed)[0] != raw:
        raise ValueError('title graphics failed decompression readback')
    target = 0xF28000
    write(target, packed, 'title graphics and prompt')
    write(descriptor, struct.pack('<III', target - descriptor, len(packed), layout),
          'title prompt descriptor')


def apply(source, write):
    relative, packed_size, layout = struct.unpack_from('<III', source, TILESET_DESCRIPTOR)
    if TILESET_DESCRIPTOR + relative != TILESET or packed_size != COMPRESSED_CAPACITY:
        raise ValueError('pause tileset descriptor differs from Japanese source')
    original, consumed = lz77.decompress(source, TILESET)
    if len(original) != 0x8000 or not 0 < consumed <= packed_size:
        raise ValueError('unexpected pause tileset dimensions')
    if lz77.decompress(lz77.compress(original))[0] != original:
        raise ValueError('pause tileset failed unchanged round trip')

    assets = bytearray(original)
    editable = set()
    for label in LABELS:
        grid = label['grid']
        before = gfxtext.canvas(original, 0, grid)
        gfxtext.draw_label(assets, 0, label)
        after = gfxtext.canvas(assets, 0, grid)
        first, last = label.get('band', (0, 7))
        if before[:first] != after[:first] or before[last + 1:] != after[last + 1:]:
            raise ValueError(f'protected rows changed for {label["text"]}')
        for row in grid:
            for tile in row:
                if tile in editable:
                    raise ValueError(f'overlapping pause label tile {tile:#x}')
                editable.add(tile)
    for tile in range(len(original) // 32):
        start = tile * 32
        if tile not in editable and original[start:start + 32] != assets[start:start + 32]:
            raise ValueError(f'protected pause tile changed at {tile:#x}')

    packed = lz77.compress(bytes(assets))
    if lz77.decompress(packed)[0] != assets:
        raise ValueError('updated pause graphics failed decompression readback')
    target = 0xF10000
    write(target, packed, 'pause menu graphics')
    write(TILESET_DESCRIPTOR, struct.pack('<III', target - TILESET_DESCRIPTOR, len(packed), layout),
          'pause graphics descriptor')
    apply_weapon_labels(source, write)
    apply_title_prompt(source, write)
    apply_codenames(source, write)
