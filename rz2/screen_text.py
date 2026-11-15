"""Opening scroll and title labels stored in the system text table."""

import struct
import gfxtext


OFFSET_TABLE = 0x34B6DC
TEXT_BASE = 0x34BC44
TEXT_END = 0x34E09C
NATIVE_COPY = 0xF00000
ROM_BASE = 0x08000000

SCROLL = (
    '시엘 일행과 헤어진 지 어느덧 1년…',
    '',
    '네오 아르카디아의 추격은 계속됐고',
    '제로는 점점 궁지에 몰렸다…',
    '', '', '', '', '',
    '제로는…',
    '시엘과 레지스탕스 동료들이',
    '걱정됐지만…',
    '',
    '눈앞의 위협을 뿌리치며',
    '살아남는 것만으로도',
    '힘에 부칠 지경이었다…',
)


def translations():
    entries = {}
    entries.update(dict.fromkeys((511, 512), '처음부터'))
    entries.update(dict.fromkeys((513, 514), '이어서'))
    entries.update(dict.fromkeys((515, 516), '둘이서 하기'))
    entries.update(dict.fromkeys(range(288, 301), '메인 장비 무기'))
    entries[301] = '서브 장비 무기'
    entries[1] = '데이터가 없습니다'
    entries[2] = '그만두기'
    entries[540] = '둘이서 하려면\n저장 데이터가 필요합니다'
    import system_text   # rz2/ko_sys/*.txt 의 나머지 시스템 문자열
    extra, _missing = system_text.load(entries)
    entries.update(extra)
    return entries


def apply(source, write, encode, glyph_width, asm):
    offsets = bytearray(source[OFFSET_TABLE:TEXT_BASE])
    original_text = source[TEXT_BASE:TEXT_END]
    # Keep the whole table in one copy. Edited strings are placed before
    # this boundary, while the remaining offsets still point to native bytes.
    text_base = NATIVE_COPY - 0x8000
    cursor = text_base
    write(NATIVE_COPY, original_text, 'native system text')
    for i, (offset,) in enumerate(struct.iter_unpack('<H', offsets)):
        struct.pack_into('<H', offsets, 2 * i, 0x8000 + offset)

    encoded = {}
    for slot, wording in translations().items():
        old = struct.unpack_from('<H', source, OFFSET_TABLE + slot * 2)[0]
        old_end = original_text.index(0xFF, old)
        original = original_text[old:old_end]
        prefix = original[:2] if original.startswith(b'\xf7') else b''
        lines = wording.split('\n')
        if 503 <= slot <= 516:
            if not prefix or sum(map(glyph_width, wording)) > 112:
                raise ValueError(f'invalid title label in slot {slot}')
        data = prefix + encode('\n'.join(lines) + '{end}')
        if data not in encoded:
            encoded[data] = cursor - text_base
            write(cursor, data, f'system text {slot}')
            cursor += len(data)
        struct.pack_into('<H', offsets, slot * 2, encoded[data])

    # Keep native positions for the cursor and center the new labels at x=120.
    for at, original_col, new_col in (
        (0xE088C, 10, 12), (0xE08AC, 10, 13), (0xE08CE, 8, 11),
    ):
        if source[at:at + 2] != bytes((original_col, 0x21)):
            raise ValueError('title prompt position mismatch')
        write(at, bytes((new_col, 0x21)), 'title label position')

    table = NATIVE_COPY + ((len(original_text) + 3) & ~3)
    write(table, offsets, 'system text offsets')
    # 되읽기 검사: 새 오프셋표(기준 text_base)가 번역 칸마다 기대 바이트를, 나머지 칸은 원본 바이트를 가리키는지
    by_slot = {}
    for slot, wording in translations().items():
        old = struct.unpack_from('<H', source, OFFSET_TABLE + slot * 2)[0]
        original = original_text[old:original_text.index(0xFF, old)]
        prefix = original[:2] if original.startswith(b'\xf7') else b''
        by_slot[slot] = prefix + encode(wording + '{end}')
    for slot in range(len(offsets) // 2):
        off = struct.unpack_from('<H', offsets, slot * 2)[0]
        if slot in by_slot:
            want = by_slot[slot]
            if encoded.get(want) != off or not (text_base <= text_base + off < NATIVE_COPY):
                raise ValueError(f'system text {slot}: offset does not point at its encoded translation')
        else:
            old = struct.unpack_from('<H', source, OFFSET_TABLE + slot * 2)[0]
            if off != 0x8000 + old:
                raise ValueError(f'system text {slot}: untranslated slot moved')
    references = {
        OFFSET_TABLE: table,
        TEXT_BASE: text_base,
    }
    for old, new in references.items():
        expected = struct.pack('<I', ROM_BASE + old)
        hits = [i for i in range(0, TEXT_END, 4) if source[i:i + 4] == expected]
        if len(hits) != 70:
            raise ValueError(f'unexpected system text reference count for {old:#x}: {len(hits)}')
        for at in hits:
            write(at, struct.pack('<I', ROM_BASE + new), f'system text reference {at:#x}')
    build_scroll(source, write, asm)


def build_scroll(source, write, asm):
    # Each visible row is 30 tiles wide and the scroll advances 16px at a time.
    # Precompose narration into BG0 tiles so scrolling never fills its VWF cache.
    tiles = bytearray(32)
    indices = {bytes(32): 0x200}
    tilemap = bytearray()
    for line in SCROLL:
        surface = [[0] * 240 for _ in range(16)]
        if line:
            width, pixels = gfxtext.text_bitmap(line, 'Galmuri11', height=11)
            left = (240 - width) // 2
            if left < 0:
                raise ValueError('opening line exceeds its 240px canvas')
            for y, row in enumerate(pixels, 2):
                surface[y][left:left + width] = row
        for top in (0, 8):
            for x in range(0, 240, 8):
                tile = bytearray(32)
                gfxtext.put_px(tile, 0, 0, [row[x:x + 8] for row in surface[top:top + 8]])
                raw = bytes(tile)
                if raw not in indices:
                    indices[raw] = 0x200 + len(tiles) // 32
                    tiles.extend(raw)
                tilemap.extend(struct.pack('<H', indices[raw]))
    expected = source[TEXT_BASE + 29:TEXT_BASE + 241]
    if len(SCROLL) != expected.count(0xFC) + 1 or max(indices.values()) >= 0x3C0:
        raise ValueError(f'opening timing or tile range exceeds the original layout ({len(indices)} tiles)')
    tile_at, map_at, code_at = 0xF20000, 0xF24000, 0xF25000
    program = '''
        push {r4-r7, lr}
        ldr r4, [sp, #20]
        subs r4, r4, r3
        lsls r0, r2, #6
        ldr r1, tilemap_target
        ldr r1, [r1]
        adds r1, r1, r0
        lsls r0, r3, #4
        subs r0, r0, r3
        lsls r0, r0, #3
        ldr r2, map_source
        adds r2, r2, r0
    rows:
        cmp r4, #0
        beq done
        cmp r3, #LINE_COUNT
        bhs done
        movs r5, #2
    half:
        movs r6, #30
    copy:
        ldrh r7, [r2]
        strh r7, [r1]
        adds r1, #2
        adds r2, #2
        subs r6, #1
        bne copy
        adds r1, #4
        subs r5, #1
        bne half
        adds r3, #1
        subs r4, #1
        b rows
    done:
        pop {r4-r7}
        pop {r0}
        bx r0
    init_scroll:
        push {r0, lr}
        ldr r2, [r0, #12]
        ldrb r2, [r2, #1]
        cmp r2, #0
        bne native
        ldr r0, asset_source
        ldr r1, bg_shadow
        ldrh r1, [r1]
        movs r2, #12
        ands r1, r2
        lsls r1, r1, #12
        ldr r2, tile_destination
        adds r1, r1, r2
        ldr r2, asset_words
    upload:
        ldmia r0!, {r3}
        stmia r1!, {r3}
        subs r2, #1
        bne upload
    native:
        pop {r0}
        pop {r3}
        mov lr, r3
        ldr r3, native_scroll
        bx r3
    .align 2
    tilemap_target: .word 0x0202F0A0
    bg_shadow: .word 0x02000F94
    tile_destination: .word 0x06004000
    native_scroll: .word 0x0801C5AD
    map_source: .word MAP_ADDRESS
    asset_source: .word ASSET_ADDRESS
    asset_words: .word WORD_COUNT
    '''
    symbols = {
        'LINE_COUNT': len(SCROLL), 'MAP_ADDRESS': ROM_BASE + map_at,
        'ASSET_ADDRESS': ROM_BASE + tile_at, 'WORD_COUNT': len(tiles) // 4,
    }
    write(tile_at, tiles, 'opening scroll tiles')
    write(map_at, tilemap, 'opening scroll tilemap')
    code_base = ROM_BASE + code_at
    code = asm.assemble(program, code_base, symbols)
    code_end = asm.label_addr(program, code_base, 'tilemap_target', symbols)
    if asm.check_thumb1(code[:code_end - code_base], code_base):
        raise ValueError('unsupported Thumb instruction in scroll renderer')
    write(code_at, code, 'opening scroll renderer')
    veneer = 0x357810
    if source[veneer:veneer + 8] != b'\xff' * 8:
        raise ValueError('unexpected opening veneer padding')
    write(veneer, bytes.fromhex('00480047') + struct.pack('<I', (ROM_BASE + code_at) | 1),
          'scroll renderer veneer')
    for at, expected in ((0x1C6B6, 'c2f0bbf8'), (0x1C6E8, 'c2f0a2f8')):
        if source[at:at + 4] != bytes.fromhex(expected):
            raise ValueError('unexpected opening renderer call')
        write(at, asm.assemble(f'bl {ROM_BASE + veneer:#x}', ROM_BASE + at), 'scroll renderer call')
    if source[0x3255F8:0x3255FC] != bytes.fromhex('adc50108'):
        raise ValueError('unexpected scroll command handler')
    init = asm.label_addr(program, ROM_BASE + code_at, 'init_scroll', symbols)
    write(0x3255F8, struct.pack('<I', init | 1), 'scroll command handler')

