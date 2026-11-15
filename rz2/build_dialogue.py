"""Build a Rockman Zero 2 development ROM with all 20 dialogue banks."""

import json
import re
import struct
import zlib

from build_poc import EXPANSION, FONT, HERE, ROOT, ROM_BASE, asm, font, kfont, make_renderer, rz1
from dump_sequel_text import TITLES, bank_ranges, load_map, read_message
import screen_gfx
import pause2_gfx
import screen_text


LEADS = range(0xEC, 0xF1)
TRAILS = 0xF0  # Payload bytes stay below every control and terminator.
HOOKS = {
    'render': (0x0DEA8C, 'f0b557464e464546'),
    'upload': (0x0DE58C, 'f0b557464e464546'),
    'count_chars': (0x0DE714, '70b5041c00252078'),
    'skip_chars': (0x0DE910, '00b50ce0ef2a01d8'),
}
TOKENS = re.compile(r'\{[^{}]+\}|.', re.DOTALL)
CONTROLS = re.compile(r'\{[^{}]+\}')
PAGES = re.compile(r'\{F[DE]\}')


def load_text():
    catalog = json.loads((ROOT / 'ref/rz2_text_inventory.json').read_text(encoding='utf-8'))
    original = {row['id']: row['jp'] for row in catalog['messages']}
    explicit = {}
    for path in sorted((HERE / 'ko').glob('*.txt')):
        for mid, text in rz1.parse_txt(path.read_text(encoding='utf-8-sig')):
            if mid not in original or mid in explicit:
                raise ValueError(f'{path.name}: unknown or repeated message {mid}')
            explicit[mid] = text
    same_source = {}
    for mid, text in explicit.items():
        same_source.setdefault(original[mid]['text'], set()).add(text)
    messages = {}
    for mid, row in original.items():
        if mid in explicit:
            text = explicit[mid]
        else:
            candidates = same_source.get(row['text'], set())
            if len(candidates) != 1:
                raise ValueError(f'missing or ambiguous translation for {mid}')
            text, = candidates
        if not text.endswith('{end}') or CONTROLS.findall(text) != CONTROLS.findall(row['text']):
            raise ValueError(f'control tokens changed for {mid}')
        limit = 224 if text.startswith('{F3:00}') or '{F3:' not in text else 160
        for page, jp_page in zip(PAGES.split(text), PAGES.split(row['text']), strict=True):
            lines = CONTROLS.sub('', page).splitlines()
            jp_lines = CONTROLS.sub('', jp_page).splitlines()
            choices = [i for i, line in enumerate(lines) if line.startswith('  ')]
            if choices != [i for i, line in enumerate(jp_lines) if line.startswith('  ')]:
                raise ValueError(f'choice rows moved for {mid}')
            widths = [sum(12 if '가' <= char <= '힣' else 8 for char in line) for line in lines]
            if len(lines) > 3 or max(widths, default=0) > limit:
                raise ValueError(f'dialogue layout exceeds bounds for {mid}')
        messages[mid] = text
    return original, messages


def make_font(source, characters):
    if len(characters) > 4 * TRAILS:
        raise ValueError('extended glyph code space exhausted')
    extra = {
        bytes((0xEC + index // TRAILS, index % TRAILS)): char
        for index, char in enumerate(sorted(characters))
    }
    bdf = kfont.load_bdf(ROOT / 'external/fonts/Galmuri11.bdf')
    table = []
    quanta = bytearray(32)
    korean_tiles = {
        (raw[0] - 0xEC + 2) * 0x100 + raw[1]: char for raw, char in extra.items()
    }
    for index in range(max(korean_tiles) + 1):
        if index in korean_tiles:
            char = korean_tiles[index]
            if char == chr(0x2002):   # 시스템 문자열 단어 사이 좁은 공백 (4px)
                width, pixels = 4, [[0] * 4 for _ in range(16)]
            else:
                width, pixels = kfont.render(bdf, char, 12 if '가' <= char <= '힣' else 8)
        elif index < 0x1F0:
            width, pixels = 8, font.glyph(source, FONT, index)
        else:
            table.append(0)
            continue
        table.append(len(quanta) // 32 | (width // 4 << 16))
        quanta.extend(kfont.to_quanta(width, pixels))
    if len(quanta) // 32 >= 0x4000:
        raise ValueError('glyph quanta exceed the tile-cache index format')
    return struct.pack(f'<{len(table)}I', *table), quanta, extra


def encode(text, codes):
    return b''.join(
        b'\xff' if token == '{end}' else
        bytes.fromhex(token[1:-1].replace(':', '')) if token.startswith('{') else
        codes[token]
        for token in TOKENS.findall(text)
    )


def main(screens=False):
    expected_crc, offset_table, text_table, bank_count = TITLES[2]
    source = (ROOT / 'roms/Rockman Zero 2 (Japan).gba').read_bytes()
    if len(source) != EXPANSION or zlib.crc32(source) != expected_crc:
        raise ValueError('Japanese ROM size or CRC mismatch')
    original, messages = load_text()
    native = load_map(ROOT / 'tools/rz234_jp_charmap.txt')
    native.update({b'\xd5': ',', b'\xe4': '…', b'\xe5': '.'})
    glyphs = {raw: char for raw, char in native.items() if raw[0] not in LEADS}
    screen_messages = screen_text.translations() if screens else {}
    visible = {
        c for text in (*messages.values(), *screen_messages.values())
        for c in CONTROLS.sub('', text) if c != '\n'
    }
    table, quanta, extra = make_font(source, visible.difference(glyphs.values()))
    glyphs.update(extra)
    codes = {char: raw for raw, char in glyphs.items()}
    codes['\n'] = b'\xfc'

    rom = bytearray(source + b'\xff' * EXPANSION)
    writes = []

    def write(offset, data, label):
        end = offset + len(data)
        if not 0 <= offset <= end <= len(rom) or any(
            offset < last and end > first for first, last, _ in writes
        ):
            raise ValueError(f'out-of-bounds or overlapping write: {label}')
        rom[offset:end] = data
        writes.append((offset, end, label))

    marker_at = EXPANSION + 0x800
    glyph_table = EXPANSION + 0x1000
    glyph_data = glyph_table + len(table)
    write(marker_at, b'RZ2 KR PATCH v0.9.3', 'marker')
    write(glyph_table, table, 'glyph table')
    write(glyph_data, quanta, 'glyph quanta')
    renderer = make_renderer(expanded=True, screens=screens)
    scanners = (HERE / 'asm/text_scan.s').read_text(encoding='utf-8')
    symbols = {'GTAB_ADDR': ROM_BASE + glyph_table, 'QDAT_ADDR': ROM_BASE + glyph_data}
    program = renderer + '\n' + scanners
    base = ROM_BASE + EXPANSION
    code = asm.assemble(program, base, symbols)
    renderer_end = asm.label_addr(program, base, 'L_GTAB', symbols)
    scanner_start = asm.label_addr(program, base, 'count_chars', symbols)
    scanner_end = asm.label_addr(program, base, 'scan_expansion', symbols)
    if len(code) > marker_at - EXPANSION or (
        asm.check_thumb1(code[:renderer_end - base], base)
        or asm.check_thumb1(code[scanner_start - base:scanner_end - base], scanner_start)
    ):
        raise ValueError('invalid Thumb renderer or scanners')
    write(EXPANSION, code, 'renderer and scanners')
    for name, (offset, before) in HOOKS.items():
        if source[offset:offset + 8] != bytes.fromhex(before):
            raise ValueError(f'{name} hook mismatch')
        target = asm.label_addr(program, base, name, symbols)
        if offset % 4 or not base <= target < base + len(code):
            raise ValueError(f'{name} hook target out of range or misaligned')
        write(offset, bytes.fromhex('004b1847') + struct.pack('<I', target | 1), name)

    cursor = (glyph_data + len(quanta) + 3) & ~3
    loaded = set()
    for bank, (old_offsets, old_base, _) in enumerate(
        bank_ranges(source, offset_table, text_table, bank_count)
    ):
        count = (old_base - old_offsets) // 2
        offsets = bytearray()
        data = bytearray()
        new_base = cursor + count * 2
        for slot in range(count):
            mid = f'{bank:02X}{slot:02X}'
            old_pointer = old_offsets + slot * 2
            old_address = old_base + struct.unpack_from('<H', source, old_pointer)[0]
            raw = bytes.fromhex(original[mid]['raw'])
            if (int(original[mid]['offset_addr'], 16) != old_pointer
                or int(original[mid]['addr'], 16) != old_address
                or source[old_address:old_address + len(raw)] != raw):
                raise ValueError(f'inventory differs from ROM for {mid}')
            offsets.extend(struct.pack('<H', len(data)))
            data.extend(encode(messages[mid], codes))
            loaded.add(mid)
        if len(data) > 0x10000:
            raise ValueError(f'bank {bank:02X} exceeds 16-bit offsets')
        write(cursor, offsets + data, f'dialogue bank {bank:02X}')
        write(offset_table + bank * 4, struct.pack('<I', ROM_BASE + cursor), 'offset pointer')
        write(text_table + bank * 4, struct.pack('<I', ROM_BASE + new_base), 'text pointer')
        cursor = (new_base + len(data) + 3) & ~3

    if loaded != messages.keys():
        raise ValueError('built message IDs differ from the translation inventory')
    if screens:
        def glyph_width(char):
            return 12 if '가' <= char <= '힣' else 4 if char == chr(0x2002) else 8

        screen_text.apply(source, write, lambda text: encode(text, codes), glyph_width, asm)
        screen_gfx.apply(source, write)
        pause2_gfx.apply(source, write)
    rom = bytes(rom)
    for bank, (offsets, text_base, bound) in enumerate(
        bank_ranges(rom, offset_table, text_table, bank_count)
    ):
        for slot in range((text_base - offsets) // 2):
            mid = f'{bank:02X}{slot:02X}'
            start = text_base + struct.unpack_from('<H', rom, offsets + slot * 2)[0]
            _, decoded = read_message(rom, start, bound, LEADS, glyphs)
            if decoded != messages[mid]:
                raise ValueError(f'ROM readback mismatch for {mid}')

    output = HERE / ('out/rz2_screens_dev.gba' if screens else 'out/rz2_dialogue_dev.gba')
    output.parent.mkdir(exist_ok=True)
    output.write_bytes(rom)
    print(f'{output}: {len(loaded)} messages, {len(extra)} added glyphs, CRC32 {zlib.crc32(rom):08X}')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--screens', action='store_true', help='also translate opening and screen labels')
    main(parser.parse_args().screens)
