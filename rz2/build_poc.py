"""Build a non-distribution RZ2 renderer PoC for the first four opening entries."""

import json
import re
import struct
import sys
import zlib
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'rz1')]
import asm
import build as rz1
import font
import kfont

ROM_BASE = 0x08000000
EXPANSION = 0x800000
FONT = 0x0EFA7C
HOOKS = {'render': 0x0DEA8C, 'upload': 0x0DE58C}
ENTRY_IDS = ('0300', '0301', '0302', '0303')
FREE_CODES = range(0xA6, 0xF0)
MARKER = b'RZ2 VWF PoC - DO NOT DISTRIBUTE'.ljust(0x20, b'\0')


def make_renderer(expanded=False, screens=False):
    source = (ROOT / 'rz1/asm/vwf.s').read_text(encoding='utf-8')
    start = source.index('    cmp r0, #0xF0\n    bhs r_ctrl')
    end = source.index('r_glyph:', start)
    # RZ2 keeps its native alphabet and F0 prefix. Its typing cursor counts
    # either form as one character.
    decoder = '''    cmp r0, #0xF0
    bhi r_ctrl
    blo r_single
    ldrb r0, [r7, #1]
    adds r0, #0xF0
    adds r7, #1
r_single:
    adds r7, #1
    subs r6, #1
'''
    if expanded:
        decoder = '''    cmp r0, #0xEC
    blo r_single
    cmp r0, #0xF0
    bhi r_native
    ldr r1, L_RZ2_EXPANSION
    cmp r7, r1
    blo r_native
NATIVE_COPY_CHECK
    subs r0, #0xEC
    adds r0, #2
    lsls r0, #8
    ldrb r1, [r7, #1]
    adds r0, r0, r1
    adds r7, #1
    b r_single
r_native:
''' + decoder
        upper_bound = '''    ldr r1, L_RZ2_NATIVE_COPY
    cmp r7, r1
    bhs r_native''' if screens else ''
        decoder = decoder.replace('NATIVE_COPY_CHECK', upper_bound)
    source = source[:start] + decoder + source[end:]
    if expanded:
        source += '\nL_RZ2_EXPANSION: .word 0x08800000\n'
    if screens:
        source += 'L_RZ2_NATIVE_COPY: .word 0x08F00000\n'
        source = source.replace(
            '4:  cmp r0, #0xF8',
            '''4:  cmp r0, #0xF7
    bne r_control_arg
    ldrb r1, [r7, #1]
    adds r1, #2
    lsls r1, r1, #28
    mov r10, r1
    adds r7, #2
    b r_fetch
r_control_arg:
    cmp r0, #0xF8''',
        ).replace(
            '    mov r3, r10\n    orrs r0, r3',
            '    mov r3, r10\n    lsls r3, r3, #16\n    lsrs r3, r3, #16\n    orrs r0, r3',
        ).replace(
            '    subs r6, r6, r5\n    strh r6, [r4]',
            '    subs r6, r6, r5\n    mov r5, r10\n    lsrs r5, r5, #16\n    orrs r5, r6\n    strh r5, [r4]',
        ).replace(
            '    adds r6, #1\n    adds r5, r4, #0',
            '    adds r5, #1\n    adds r6, r4, #0',
        ).replace(
            '    adds r5, #0x40\n    strh r6, [r5]',
            '    adds r6, #0x40\n    strh r5, [r6]',
        )
    if expanded:
        # Bit 15 of the right half marks a dirty tile. Store its own
        # highlight in bit 14, including when a tile pairs two glyphs.
        source = source.replace(
            '    adds r1, r0, #0\n    adds r0, r2, #0\n    bl cell',
            '''    adds r1, r0, #0
    cmp r1, #0
    beq emit_right_ready
    mov r3, r10
    lsls r3, r3, #16
    lsrs r3, r3, #17
    orrs r1, r3
emit_right_ready:
    adds r0, r2, #0
    bl cell''',
        )
        if not screens:
            source = source.replace(
                '    lsls r3, r3, #16\n    lsrs r3, r3, #17',
                '    lsrs r3, r3, #1',
            )
        source = source.replace(
            '    lsls r1, r1, #5\n    adds r6, r1, r2',
            '''    lsls r7, r1, #17
    lsrs r7, r7, #31
    lsls r7, r7, #1
    mov r8, r7
    lsls r1, r1, #18
    lsrs r1, r1, #13
    adds r6, r1, r2''',
        )
        source = source.replace(
            'upload:\n    push {r4-r7, lr}',
            'upload:\n    push {r4-r7, lr}\n    mov r0, r8\n    push {r0}',
        ).replace(
            '''    lsls r2, r2, #16
    orrs r1, r2
    cmp r0, #0
    beq 1f
    lsls r1, r1, #2
1:  stmia r3!, {r1}''',
            '''    cmp r0, #1
    beq upload_highlight_left
    cmp r0, #3
    bne upload_left_ready
upload_highlight_left:
    lsls r1, r1, #2
upload_left_ready:
    cmp r0, #2
    blo upload_right_ready
    lsls r2, r2, #2
upload_right_ready:
    lsls r2, r2, #16
    orrs r1, r2
    stmia r3!, {r1}''',
        ).replace(
            'u_end:\n    pop {r4-r7}',
            'u_end:\n    pop {r0}\n    mov r8, r0\n    pop {r4-r7}',
        ).replace(
            '    lsrs r0, r0, #15',
            '    lsrs r0, r0, #15\n    add r0, r8',
        )
    for original, sequel in {
        '0x02023634': '0x0202F634',
        '0x02023628': '0x0202F628',
        '0x0202362C': '0x0202F62C',
        '0x02023630': '0x0202F630',
        '0x02023620': '0x0202F620',
        '0x02004F34': '0x02000F94',
    }.items():
        source = source.replace(original, sequel)
    return source


def main():
    source = (ROOT / 'roms/Rockman Zero 2 (Japan).gba').read_bytes()
    if zlib.crc32(source) != 0x9B5C8A4C:
        raise ValueError('Japanese ROM CRC mismatch')
    inventory = json.loads((ROOT / 'ref/rz2_text_inventory.json').read_text(encoding='utf-8'))
    rows = {entry['id']: entry['jp'] for entry in inventory['messages']}
    translations = dict(rz1.parse_txt((HERE / 'ko/opening.txt').read_text(encoding='utf-8')))
    selected = [translations[mid] for mid in ENTRY_IDS]
    syllables = sorted({char for text in selected for char in text if '가' <= char <= '힣'})
    if len(syllables) > len(FREE_CODES):
        raise ValueError('PoC font slots exhausted')
    korean = dict(zip(syllables, FREE_CODES))
    for row in rows.values():
        raw = bytes.fromhex(row['raw'])
        if any(lead == 0xF0 and tail in korean.values() for lead, tail in zip(raw, raw[1:])):
            raise ValueError('PoC glyph overlaps existing F0 pair')

    # Keep Japanese glyphs at their native 8px widths on all existing paths.
    font_data = kfont.load_bdf(ROOT / 'external/fonts/Galmuri11.bdf')
    replacement = {0xF0 + code: char for char, code in korean.items()}
    qdat = bytearray(32)
    table = []
    for code in range(0x1F0):
        if code in replacement:
            width, pixels = kfont.render(font_data, replacement[code], 12)
        else:
            width, pixels = 8, font.glyph(source, FONT, code)
        table.append((len(qdat) // 32) | (width // 4 << 16))
        qdat.extend(kfont.to_quanta(width, pixels))

    encode_latin = {char: bytes.fromhex(code) for code, char in (
        line.split('=', 1)
        for line in (ROOT / 'tools/rz234_jp_charmap.txt').read_text(encoding='utf-8').splitlines()
        if line and not line.startswith('#')
    )}
    encode_latin.update({'\n': b'\xFC', '…': b'\xE4', ',': b'\xD5', '.': b'\xE5'})
    encode_latin.update({char: bytes((0xF0, code)) for char, code in korean.items()})

    rom = bytearray(source + b'\xFF' * EXPANSION)
    marker_at = EXPANSION + 0x800
    rom[marker_at:marker_at + len(MARKER)] = MARKER
    gtab_at = EXPANSION + 0x1000
    qdat_at = gtab_at + len(table) * 4
    rom[gtab_at:qdat_at] = struct.pack(f'<{len(table)}I', *table)
    rom[qdat_at:qdat_at + len(qdat)] = qdat
    program = make_renderer()
    symbols = {'GTAB_ADDR': ROM_BASE + gtab_at, 'QDAT_ADDR': ROM_BASE + qdat_at}
    code = asm.assemble(program, ROM_BASE + EXPANSION, symbols)
    literal = asm.label_addr(program, ROM_BASE + EXPANSION, 'L_GTAB', symbols)
    if len(code) > 0x800 or asm.check_thumb1(code[:literal - ROM_BASE - EXPANSION], ROM_BASE + EXPANSION):
        raise ValueError('invalid renderer')
    rom[EXPANSION:EXPANSION + len(code)] = code
    for name, offset in HOOKS.items():
        if rom[offset:offset + 8] != bytes.fromhex('f0b557464e464546'):
            raise ValueError(f'{name} hook mismatch')
        target = asm.label_addr(program, ROM_BASE + EXPANSION, name, symbols)
        rom[offset:offset + 8] = bytes.fromhex('004b1847') + struct.pack('<I', target | 1)

    bank = [row for mid, row in rows.items() if mid.startswith('03')]
    offset_table = (qdat_at + len(qdat) + 3) & ~3
    text_base = offset_table + len(bank) * 2
    cursor = text_base
    for index, row in enumerate(bank):
        mid = f'03{index:02X}'
        raw = bytes.fromhex(row['raw'])
        address = int(row['addr'], 16)
        if source[address:address + len(raw)] != raw:
            raise ValueError(f'inventory differs from source ROM for {mid}')
        if mid in ENTRY_IDS:
            text = translations[mid]
            if re.findall(r'\{[^}]+\}', text) != re.findall(r'\{[^}]+\}', row['text']):
                raise ValueError(f'control tokens changed for {mid}')
            raw = b''.join(
                b'\xff' if token == '{end}' else
                bytes.fromhex(token[1:-1].replace(':', '')) if token.startswith('{') else
                encode_latin[token]
                for token in re.findall(r'\{[^{}]+\}|.', text, flags=re.DOTALL)
            )
        struct.pack_into('<H', rom, offset_table + index * 2, cursor - text_base)
        rom[cursor:cursor + len(raw)] = raw
        cursor += len(raw)
    struct.pack_into('<I', rom, 0x34E0A8 + 12, ROM_BASE + offset_table)
    struct.pack_into('<I', rom, 0x34E0F8 + 12, ROM_BASE + text_base)
    if len(rom) != 2 * EXPANSION or rom[marker_at:marker_at + len(MARKER)] != MARKER:
        raise ValueError('invalid PoC size or missing non-distribution marker')
    output = HERE / 'out/rz2_vwf_poc.gba'
    output.parent.mkdir(exist_ok=True)
    output.write_bytes(rom)
    print(f'{output}: {len(ENTRY_IDS)} messages, {len(korean)} syllables, CRC32 {zlib.crc32(rom):08X}')


if __name__ == '__main__':
    main()
