"""록맨 제로 3 대사 빌드: 2편 가변폭 출력기를 3편 주소로 옮겨 쓴다.

- 번역이 다 찬 뱅크만 확장 영역(0x800000~)으로 옮겨 EC~F0 두 바이트 한글로 다시 쓴다.
  덜 찬 뱅크는 원래 자리의 일본어 그대로 둔다(출력기는 포인터 위치로 두 방식을 가른다).
- 3편 출력 함수는 (x, y, 문자열, 글자 수)를 받는다. r3 가 인자라서 렌더 훅은 ARM 경유
  (ip 레지스터)로 shim 에 들어가, 타일맵 포인터 [0x02030310] + (y*32+x)*2 를 만들어
  2편 출력기(목적지, 문자열, 글자 수)를 부른다.
"""

import argparse
import json
import re
import struct
import sys
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path[:0] = [str(HERE), str(ROOT / 'tools'), str(ROOT / 'rz2'), str(ROOT / 'rz1')]

import asm
import font
import kfont
from build_poc import make_renderer
from dump_sequel_text import TITLES, bank_ranges, load_map, read_message
import build as rz1   # parse_txt
import screen_text   # rz3/screen_text.py (sys.path 맨 앞이 rz3)
import logo_rz3
import logo_strip_rz3
import title_prompt
import scroll
import pause3_gfx

ROM_BASE = 0x08000000
EXPANSION = 0x800000
FONT = 0x0FF17C
LEADS = range(0xEC, 0xF1)
TRAILS = 0xF0
TILEMAP_PTR = 0x02030310
# 2편 RAM -> 3편 RAM (캐시 노드·이름 포인터·BG 그림자)
RAM = {
    '0x0202F634': '0x020308A4', '0x0202F628': '0x02030898', '0x0202F62C': '0x0203089C',
    '0x0202F630': '0x020308A0', '0x0202F620': '0x02030890', '0x02000F94': '0x02002144',
}
HOOKS = {   # 이름: (위치, 원본 8바이트)
    'upload': (0x0E98EC, 'f0b557464e464546'),
    'count_chars': (0x0E9A74, '70b5041c00252078'),
    'skip_chars': (0x0E9C88, '00b50ce0ef2a01d8'),
}
RENDER_HOOK = (0x0E9E00, 'f0b557464e464546e0b484b0171c0006')   # 덮는 16바이트
TOKENS = re.compile(r'\{[^{}]+\}|.', re.DOTALL)
CONTROLS = re.compile(r'\{[^{}]+\}')
PAGES = re.compile(r'\{F[DE]\}')

SHIM = '''
render_xy:
    push {r4, lr}
    lsls r0, r0, #24
    lsrs r0, r0, #24
    lsls r1, r1, #24
    lsrs r1, r1, #24
    lsls r1, r1, #5
    adds r1, r1, r0
    lsls r1, r1, #1
    ldr r4, L_TILEMAP
    ldr r4, [r4]
    adds r0, r4, r1
    adds r1, r2, #0
    adds r2, r3, #0
    bl render
    pop {r4}
    pop {r1}
    bx r1
.align 2
L_TILEMAP: .word TILEMAP_PTR
'''


def width(line):
    return sum(12 if '가' <= c <= '힣' else 8 for c in line)


def load_text():
    catalog = json.loads((ROOT / 'ref/rz3_text_inventory.json').read_text(encoding='utf-8'))
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
    messages, problems = {}, []
    for mid, row in original.items():
        text = explicit.get(mid)
        if text is None:
            candidates = same_source.get(row['text'], set())
            if len(candidates) != 1:
                continue
            text, = candidates
        if not text.endswith('{end}') or CONTROLS.findall(text) != CONTROLS.findall(row['text']):
            problems.append(f'{mid}: control tokens differ from the original')
            continue
        speaker = None   # 초상화 없음(F3 없음·00·02)이면 224px, 초상화 대사는 160px
        for page, jp_page in zip(PAGES.split(text), PAGES.split(row['text']), strict=True):
            for code in re.findall(r'\{F3:(..)\}', page):
                speaker = code
            limit = 224 if speaker in (None, '00', '02') else 160
            lines = CONTROLS.sub('', page).splitlines()
            jp_lines = CONTROLS.sub('', jp_page).splitlines()
            choices = [i for i, line in enumerate(lines) if line.startswith('  ')]
            if choices != [i for i, line in enumerate(jp_lines) if line.startswith('  ')]:
                problems.append(f'{mid}: choice rows moved')
            for line in lines:
                if width(line) > limit:
                    problems.append(f'{mid}: {width(line)}px > {limit}px: {line}')
            if len(lines) > 3:
                problems.append(f'{mid}: {len(lines)} lines on a page')
        messages[mid] = text
    if problems:
        unique = list({q.split(': ', 1)[1]: q for q in reversed(problems)}.values())[::-1]   # 공유 칸 중복 제거
        raise ValueError('layout check failed:\n  ' + '\n  '.join(unique))
    return original, messages


def make_font(source, characters):
    if len(characters) > 4 * TRAILS:
        raise ValueError('extended glyph code space exhausted')
    extra = {bytes((0xEC + i // TRAILS, i % TRAILS)): c for i, c in enumerate(sorted(characters))}
    bdf = kfont.load_bdf(ROOT / 'external/fonts/Galmuri11.bdf')
    korean = {(raw[0] - 0xEC + 2) * 0x100 + raw[1]: c for raw, c in extra.items()}
    table, quanta = [], bytearray(32)
    for index in range(max(korean, default=0x1EF) + 1):
        if index in korean:
            c = korean[index]
            w, pixels = (4, [[0] * 4 for _ in range(16)]) if c == chr(0x2002) else \
                kfont.render(bdf, c, 12 if '가' <= c <= '힣' else 8)
        elif index < 0x1F0:
            w, pixels = 8, font.glyph(source, FONT, index)
        else:
            table.append(0)
            continue
        table.append(len(quanta) // 32 | (w // 4 << 16))
        quanta.extend(kfont.to_quanta(w, pixels))
    if len(quanta) // 32 >= 0x4000:
        raise ValueError('glyph quanta exceed the tile-cache index format')
    return struct.pack(f'<{len(table)}I', *table), quanta, extra


def encode(text, codes):
    return b''.join(
        b'\xff' if t == '{end}' else
        bytes.fromhex(t[1:-1].replace(':', '')) if t.startswith('{') else codes[t]
        for t in TOKENS.findall(text))


def main(out):
    expected_crc, offset_table, text_table, bank_count = TITLES[3]
    source = (ROOT / 'roms/Rockman Zero 3 (Japan).gba').read_bytes()
    if len(source) != EXPANSION or zlib.crc32(source) != expected_crc:
        raise ValueError('Japanese ROM size or CRC mismatch')
    original, messages = load_text()
    native = load_map(ROOT / 'tools/rz234_jp_charmap.txt')
    native.update({b'\xd5': ',', b'\xe4': '…', b'\xe5': '.'})
    glyphs = {raw: c for raw, c in native.items() if raw[0] not in LEADS}

    banks = list(bank_ranges(source, offset_table, text_table, bank_count))
    full = [b for b, (offs, base, _) in enumerate(banks)
            if all(f'{b:02X}{s:02X}' in messages for s in range((base - offs) // 2))]
    used = {mid for mid in messages if int(mid[:2], 16) in full}
    system = screen_text.translations()
    visible = {c for text in (*(messages[mid] for mid in used), *system.values())
               for c in CONTROLS.sub('', text) if c != '\n'}
    table, quanta, extra = make_font(source, visible.difference(glyphs.values()))
    glyphs.update(extra)
    codes = {c: raw for raw, c in glyphs.items()}
    codes['\n'] = b'\xfc'

    rom = bytearray(source + b'\xff' * EXPANSION)
    writes = []

    def write(offset, data, label):
        end = offset + len(data)
        if not 0 <= offset <= end <= len(rom) or any(offset < b and end > a for a, b, _ in writes):
            raise ValueError(f'out-of-bounds or overlapping write: {label}')
        rom[offset:end] = data
        writes.append((offset, end, label))

    marker_at = EXPANSION + 0x800
    glyph_table = EXPANSION + 0x1000
    glyph_data = glyph_table + len(table)
    write(marker_at, b'RZ3 KR PATCH v0.9.2', 'marker')
    write(glyph_table, table, 'glyph table')
    write(glyph_data, quanta, 'glyph quanta')

    renderer = make_renderer(expanded=True, screens=True)
    # 3편 F7: 팔레트 = [0x02030310+6] + 인수 (2편은 인수 + 2)
    f7_2 = '''    ldrb r1, [r7, #1]
    adds r1, #2
    lsls r1, r1, #28
'''
    f7_3 = '''    ldrb r1, [r7, #1]
    push {r2}
    ldr r2, L_TEXTSYS
    ldrh r2, [r2, #6]
    adds r1, r1, r2
    pop {r2}
    lsls r1, r1, #28
'''
    if renderer.count(f7_2) != 1:
        raise ValueError('F7 palette code not found in the renderer')
    renderer = renderer.replace(f7_2, f7_3) + '''L_TEXTSYS: .word 0x02030310
'''
    for old, new in RAM.items():
        renderer = renderer.replace(old, new)
    scanners = (ROOT / 'rz2/asm/text_scan.s').read_text(encoding='utf-8')
    scanners = scanners.replace('count_return:   .word 0x080DE71D', 'count_return:   .word 0x080E9A7D')
    if '0x080E9A7D' not in scanners:
        raise ValueError('text scanner return address was not replaced')
    program = renderer + '\n' + scanners + '\n' + SHIM
    symbols = {'GTAB_ADDR': ROM_BASE + glyph_table, 'QDAT_ADDR': ROM_BASE + glyph_data,
               'TILEMAP_PTR': TILEMAP_PTR}
    base = ROM_BASE + EXPANSION
    code = asm.assemble(program, base, symbols)
    checks = [('render', 'L_GTAB'), ('count_chars', 'scan_expansion'), ('render_xy', 'L_TILEMAP')]
    for first, last in checks:
        a = asm.label_addr(program, base, first, symbols)
        b = asm.label_addr(program, base, last, symbols)
        if asm.check_thumb1(code[a - base:b - base], a):
            raise ValueError(f'invalid Thumb-1 code in {first}')
    if len(code) > marker_at - EXPANSION:
        raise ValueError('renderer does not fit before the marker')
    write(EXPANSION, code, 'renderer, scanners and shim')
    for name, (offset, before) in HOOKS.items():
        if source[offset:offset + 8] != bytes.fromhex(before):
            raise ValueError(f'{name} hook mismatch')
        target = asm.label_addr(program, base, name, symbols)
        if offset % 4:
            raise ValueError(f'{name} hook misaligned')
        write(offset, bytes.fromhex('004b1847') + struct.pack('<I', target | 1), name)
    # 렌더 훅: bx pc / nop 로 ARM 전환 -> ldr ip,[pc] / bx ip / .word shim|1 (r0~r3 보존)
    offset, before = RENDER_HOOK
    if source[offset:offset + len(before) // 2] != bytes.fromhex(before) or offset % 4:
        raise ValueError('render hook mismatch')
    shim = asm.label_addr(program, base, 'render_xy', symbols)
    write(offset, bytes.fromhex('7847c046') + struct.pack('<III', 0xE59FC000, 0xE12FFF1C, shim | 1),
          'render hook')

    cursor = (glyph_data + len(quanta) + 3) & ~3
    for bank in full:
        old_offsets, old_base, _ = banks[bank]
        count = (old_base - old_offsets) // 2
        offsets, data = bytearray(), bytearray()
        new_base = cursor + count * 2
        for slot in range(count):
            mid = f'{bank:02X}{slot:02X}'
            pointer = old_offsets + slot * 2
            address = old_base + struct.unpack_from('<H', source, pointer)[0]
            raw = bytes.fromhex(original[mid]['raw'])
            if int(original[mid]['offset_addr'], 16) != pointer or int(original[mid]['addr'], 16) != address \
                    or source[address:address + len(raw)] != raw:
                raise ValueError(f'inventory differs from ROM for {mid}')
            offsets += struct.pack('<H', len(data))
            data += encode(messages[mid], codes)
        if len(data) > 0x10000:
            raise ValueError(f'bank {bank:02X} exceeds 16-bit offsets')
        write(cursor, offsets + data, f'dialogue bank {bank:02X}')
        write(offset_table + bank * 4, struct.pack('<I', ROM_BASE + cursor), 'offset pointer')
        write(text_table + bank * 4, struct.pack('<I', ROM_BASE + new_base), 'text pointer')
        cursor = (new_base + len(data) + 3) & ~3

    system_slots = screen_text.apply(source, write, lambda text: encode(text, codes))
    logo_rz3.apply(source, write)   # 타이틀 로고 「록맨®제로」
    logo_strip_rz3.apply(source, write)   # 로고 등장 연출의 글자 띠(스프라이트)
    title_prompt.apply(source, write)   # 시작 안내
    scroll.apply(source, write, asm)   # 오프닝 스크롤(줄 타일 슬롯)
    pause3_gfx.apply(source, write)   # 서브 화면 그림 글자
    rom = bytes(rom)
    # 되읽기: 옮긴 뱅크는 원고와, 나머지 뱅크는 원본과 같아야 한다.
    for bank, (offs, tbase, bound) in enumerate(bank_ranges(rom, offset_table, text_table, bank_count)):
        if bank not in full:   # 원래 자리 그대로인지(포인터·본문) 원본과 대조
            if (offs, tbase) != banks[bank][:2] or rom[offs:bound] != source[offs:bound]:
                raise ValueError(f'untouched bank {bank:02X} changed')
            continue
        for slot in range((tbase - offs) // 2):
            mid = f'{bank:02X}{slot:02X}'
            start = tbase + struct.unpack_from('<H', rom, offs + slot * 2)[0]
            _, decoded = read_message(rom, start, bound, LEADS, glyphs)
            if decoded != messages[mid]:
                raise ValueError(f'ROM readback mismatch for {mid}')
    out.parent.mkdir(exist_ok=True)
    out.write_bytes(rom)
    done = sum(1 for b in full for _ in range((banks[b][1] - banks[b][0]) // 2))
    print(f'{out}: banks {[f"{b:02X}" for b in full]}, {done}/{len(original)} messages, '
          f'{len(extra)} glyphs, {system_slots} system strings, CRC32 {zlib.crc32(rom):08X}')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, default=HERE / 'out/rz3_dev.gba')
    main(ap.parse_args().out)
