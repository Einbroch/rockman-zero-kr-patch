"""록맨 제로 4 대사 빌드: 3편 빌드(rz3/build_dialogue.py)를 4편 주소로 옮긴 것.

4편 일본판은 이미 16MB 라서 롬을 늘릴 수 없다. 그래서 한글 판정 구간을 따로 정한다.
- 출력기·스캐너는 포인터가 [KLO, KHI) 안이면 EC~F0 두 바이트 한글, 밖이면 원래 인코딩으로 읽는다.
- 번역 중(뱅크 일부만 완성): 구간 = 빈 덩어리 [0x882440, 0x8A7000). 일본어 대사·시스템 문자열은
  원래 자리(0x86CFF8~0x88126D, 구간 아래)에 그대로 둔다.
- 대사 전부 완성 후: 구간을 원래 대사 자리(0x870D24, 뱅크 포인터표 바로 뒤)까지 넓힌다.
- 코드·표식은 구간 밖 빈 조각(0xC37250, 0x4000 경계로 끝나는 0xFF 패딩)에 둔다.
4편 출력 함수는 3편과 같은 (x, y, 문자열, 글자 수) 형태라 3편 shim 을 그대로 쓴다.
"""

import argparse
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
import rz4_system_text as system_text
import pause4_gfx
import title_prompt4
import gameover4
import logo4
import opening4

sys.path.insert(0, str(ROOT / 'rz3'))
import importlib.util
_spec = importlib.util.spec_from_file_location('rz3_build', ROOT / 'rz3/build_dialogue.py')
# 3편 빌드의 검사·인코딩 함수만 빌려 쓴다(3편 모듈 최상위 import 는 rz3 경로를 요구).
rz3 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rz3)

ROM_BASE = 0x08000000
ROM_SIZE = 0x1000000
FONT = 0x12A56C
LEADS = range(0xEC, 0xF1)
TRAILS = 0xF0
TILEMAP_PTR = 0x0202EDC0
# 2편 RAM -> 4편 RAM (3편 주소 -0x1550, BG 그림자는 0x02000A04)
RAM = {
    '0x0202F634': '0x0202F354', '0x0202F628': '0x0202F348', '0x0202F62C': '0x0202F34C',
    '0x0202F630': '0x0202F350', '0x0202F620': '0x0202F340', '0x02000F94': '0x02000A04',
}
HOOKS = {   # 이름: (위치, 원본 8바이트) — 3편과 같은 바이트(함수 동일)
    'upload': (0x10D664, 'f0b557464e464546'),
    'count_chars': (0x10D7EC, '70b5041c00252078'),
    'skip_chars': (0x10DA00, '00b50ce0ef2a01d8'),
}
COUNT_RETURN = 0x0810D7F5
RENDER_HOOK = (0x10DBDC, 'f0b557464e464546e0b484b0171c0006')
CODE_AT, CODE_END = 0xC37250, 0xC3C000
SYS_TABLE, SYS_TEXT, SYS_SLOTS = 0x86CFF8, 0x86D6B4, 862   # 시스템 문자열 오프셋표·본문(참조 153·146곳)          # 구간 밖 빈 조각
WINDOW_PARTIAL = (0x882440, 0x8A7000)
WINDOW_FULL = (0x870DBC, 0x8A7000)   # 0x870D24~0x870DBB 152바이트는 대사가 아닌 데이터(덮으면 초상화가 깨짐)
DIALOGUE_SPAN = (0x870DBC, 0x88126D)             # 첫 뱅크 오프셋표 ~ 마지막 메시지 끝(전 바이트가 대사임을 확인)


def load_text():
    rz3.ROOT, rz3.HERE = ROOT, HERE
    saved = rz3.json.loads
    catalog_path = ROOT / 'ref/rz4_text_inventory.json'
    original_text = catalog_path.read_text(encoding='utf-8')
    # rz3.load_text 는 rz3 인벤토리를 읽으므로 경로만 4편 것으로 바꿔 부른다.
    real_read = Path.read_text

    def read_text(self, *a, **k):
        if self.name == 'rz3_text_inventory.json':
            return original_text
        return real_read(self, *a, **k)
    Path.read_text = read_text
    try:
        return rz3.load_text()
    finally:
        Path.read_text = real_read
        rz3.json.loads = saved


def make_font(source, characters, keep_native):
    """3편 make_font 와 같되, 원본 글리프 중 한자 영역(0xF0~0x1EF)은 keep_native 에 든 것만 넣는다.
    4편은 롬 공간이 빠듯해서(전부 넣으면 15KB) 실제 쓰는 것만 남긴다. 빠진 칸은 폭 0(그리지 않음)."""
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
        elif index < 0xF0 or (index < 0x1F0 and index in keep_native):
            w, pixels = 8, font.glyph(source, FONT, index)
        else:
            table.append(0)
            continue
        table.append(len(quanta) // 32 | (w // 4 << 16))
        quanta.extend(kfont.to_quanta(w, pixels))
    if len(quanta) // 32 >= 0x4000:
        raise ValueError('glyph quanta exceed the tile-cache index format')
    return struct.pack(f'<{len(table)}I', *table), quanta, extra


def native_indices(raw):
    """원래 인코딩 문자열이 쓰는 글리프 번호들 (F0 xx = 0xF0+xx, F3~F8 은 인수 1바이트)."""
    out, i = set(), 0
    while i < len(raw) and raw[i] != 0xFF:
        b = raw[i]
        if b == 0xF0:
            out.add(0xF0 + raw[i + 1]); i += 2
        elif b < 0xF0:
            out.add(b); i += 1
        else:
            i += 2 if 0xF3 <= b <= 0xF8 else 1
    return out


def main(out):
    expected_crc, offset_table, text_table, bank_count = TITLES[4]
    source = (ROOT / 'roms/Rockman Zero 4 (Japan).gba').read_bytes()
    if len(source) != ROM_SIZE or zlib.crc32(source) != expected_crc:
        raise ValueError('Japanese ROM size or CRC mismatch')
    original, messages = load_text()
    native = load_map(ROOT / 'tools/rz234_jp_charmap.txt')
    native.update({b'\xd5': ',', b'\xe4': '…', b'\xe5': '.'})
    glyphs = {raw: c for raw, c in native.items() if raw[0] not in LEADS}

    banks = list(bank_ranges(source, offset_table, text_table, bank_count))
    # 옛 대사 자리를 덮어써도 되는지: 구간의 모든 바이트가 메시지 본문이나 오프셋표여야 한다.
    covered = bytearray(DIALOGUE_SPAN[1] - DIALOGUE_SPAN[0])
    for row in original.values():
        for at, n in ((int(row['addr'], 16), len(bytes.fromhex(row['raw']))), (int(row['offset_addr'], 16), 2)):
            for i in range(max(at, DIALOGUE_SPAN[0]), min(at + n, DIALOGUE_SPAN[1])):
                covered[i - DIALOGUE_SPAN[0]] = 1
    for i, c in enumerate(covered):   # 뱅크 사이 정렬 패딩(0 이 3바이트 이하, 다음 뱅크가 4바이트 정렬)만 허용
        at = DIALOGUE_SPAN[0] + i
        if not c and not (source[at] == 0 and ((at + 3) & ~3) - at < 4 and
                          all(covered[j - DIALOGUE_SPAN[0]] or source[j] == 0 for j in range(at, (at + 4) & ~3))):
            raise ValueError(f'non-dialogue byte inside DIALOGUE_SPAN at {at:#x}')
    full = [b for b, (offs, base, _) in enumerate(banks)
            if all(f'{b:02X}{s:02X}' in messages for s in range((base - offs) // 2))]
    klo, khi = WINDOW_FULL if len(full) == bank_count else WINDOW_PARTIAL
    if source[CODE_AT:CODE_END] != b'\xff' * (CODE_END - CODE_AT):
        raise ValueError('code area is not free')
    if source[WINDOW_PARTIAL[0]:WINDOW_PARTIAL[1]] != b'\xff' * (WINDOW_PARTIAL[1] - WINDOW_PARTIAL[0]):
        raise ValueError('free block is not free')
    used = {mid for mid in messages if int(mid[:2], 16) in full}
    system, _missing = system_text.load({}) if len(full) == bank_count else ({}, [])
    visible = {c for text in (*(messages[mid] for mid in used), *system.values())
               for c in rz3.CONTROLS.sub('', text) if c != '\n'}
    # 남겨 둘 원본 한자 글리프: 한글 원고가 원래 글리프로 쓰는 문자 + 번역 안 한 시스템 문자열이 쓰는 글리프
    sys_offsets = struct.unpack_from(f'<{SYS_SLOTS}H', source, SYS_TABLE)
    keep = {0xF0 + raw[1] if raw[0] == 0xF0 else raw[0] for raw, c in glyphs.items() if c in visible}
    for slot, off in enumerate(sys_offsets):
        if slot not in system:
            keep |= native_indices(source[SYS_TEXT + off:SYS_TEXT + off + 0x400])
    if len(full) != bank_count:   # 번역 중엔 일본어 대사 뱅크도 원래 글리프를 쓴다
        keep = set(range(0x1F0))
    table, quanta, extra = make_font(source, visible.difference(glyphs.values()), keep)
    glyphs.update(extra)
    codes = {c: raw for raw, c in glyphs.items()}
    codes['\n'] = b'\xfc'

    rom = bytearray(source)
    writes = []

    def write(offset, data, label):
        end = offset + len(data)
        if not 0 <= offset <= end <= len(rom) or any(offset < b and end > a for a, b, _ in writes):
            raise ValueError(f'out-of-bounds or overlapping write: {label}')
        rom[offset:end] = data
        writes.append((offset, end, label))

    renderer = make_renderer(expanded=True, screens=True)
    f7_2 = '''    ldrb r1, [r7, #1]
    adds r1, #2
    lsls r1, r1, #28
'''
    f7_4 = '''    ldrb r1, [r7, #1]
    push {r2}
    ldr r2, L_TEXTSYS
    ldrh r2, [r2, #6]
    adds r1, r1, r2
    pop {r2}
    lsls r1, r1, #28
'''
    if renderer.count(f7_2) != 1:
        raise ValueError('F7 palette code not found in the renderer')
    renderer = renderer.replace(f7_2, f7_4) + f'L_TEXTSYS: .word {TILEMAP_PTR:#010x}\n'
    for old, new in RAM.items():
        renderer = renderer.replace(old, new)
    for old, new in (('L_RZ2_EXPANSION: .word 0x08800000', f'L_RZ2_EXPANSION: .word {ROM_BASE + klo:#010x}'),
                     ('L_RZ2_NATIVE_COPY: .word 0x08F00000', f'L_RZ2_NATIVE_COPY: .word {ROM_BASE + khi:#010x}')):
        if renderer.count(old) != 1:
            raise ValueError(f'renderer literal not found: {old}')
        renderer = renderer.replace(old, new)
    scanners = (ROOT / 'rz2/asm/text_scan.s').read_text(encoding='utf-8')
    for old, new in (
        ('count_return:   .word 0x080DE71D', f'count_return:   .word {COUNT_RETURN:#010x}'),
        ('scan_expansion: .word 0x08800000', f'scan_expansion: .word {ROM_BASE + klo:#010x}\n'
                                             f'scan_limit:     .word {ROM_BASE + khi:#010x}'),
        # 4편은 구간 위에도 원래 인코딩 문자열이 있으므로 상한도 본다.
        ('    blo count_native\n', '    blo count_native\n    ldr r1, scan_limit\n    cmp r0, r1\n'
                                   '    bhs count_native\n'),
        ('    blo skip_native\n', '    blo skip_native\n    ldr r2, scan_limit\n    cmp r0, r2\n'
                                  '    bhs skip_native\n'),
    ):
        if scanners.count(old) != 1:
            raise ValueError(f'scanner text not found: {old.strip()}')
        scanners = scanners.replace(old, new)
    program = renderer + '\n' + scanners + '\n' + rz3.SHIM
    base = ROM_BASE + CODE_AT
    marker = b'RZ4 KR PATCH v0.9.1'
    # 코드 -> 표식 -> 글리프 표 순으로 구간 밖 조각에, 글리프 조각(quanta)은 구간 안 빈 덩어리에 둔다.
    # 한글 데이터 빈 구간: 번역 중엔 빈 덩어리만, 전체 모드에선 옛 대사 자리도 쓴다(사이 데이터는 건너뜀).
    free = [list(WINDOW_PARTIAL)] if klo == WINDOW_PARTIAL[0] else [list(DIALOGUE_SPAN), list(WINDOW_PARTIAL)]

    def alloc(size, label, limit=None):
        for seg in free:
            start = (seg[0] + 3) & ~3
            if start + size <= seg[1] and (limit is None or start + size <= limit):
                seg[0] = start + size
                return start
        raise ValueError(f'{label} ({size} bytes) does not fit the Korean window; left {[b - a for a, b in free]}')
    glyph_data = alloc(len(quanta), 'glyph quanta')
    symbols = {'GTAB_ADDR': 0, 'QDAT_ADDR': ROM_BASE + glyph_data, 'TILEMAP_PTR': TILEMAP_PTR}
    code = asm.assemble(program, base, symbols)
    marker_at = CODE_AT + ((len(code) + 15) & ~15)
    glyph_table = (marker_at + len(marker) + 15) & ~15
    if glyph_table + len(table) > CODE_END:
        raise ValueError('code, marker and glyph table do not fit the code area')
    symbols['GTAB_ADDR'] = ROM_BASE + glyph_table
    code = asm.assemble(program, base, symbols)
    for first, last in (('render', 'L_GTAB'), ('count_chars', 'scan_expansion'), ('render_xy', 'L_TILEMAP')):
        a = asm.label_addr(program, base, first, symbols)
        b = asm.label_addr(program, base, last, symbols)
        if asm.check_thumb1(code[a - base:b - base], a):
            raise ValueError(f'invalid Thumb-1 code in {first}')
    write(CODE_AT, code, 'renderer, scanners and shim')
    write(marker_at, marker, 'marker')
    write(glyph_table, table, 'glyph table')
    write(glyph_data, quanta, 'glyph quanta')
    for name, (offset, before) in HOOKS.items():
        if source[offset:offset + 8] != bytes.fromhex(before) or offset % 4:
            raise ValueError(f'{name} hook mismatch')
        target = asm.label_addr(program, base, name, symbols)
        write(offset, bytes.fromhex('004b1847') + struct.pack('<I', target | 1), name)
    offset, before = RENDER_HOOK
    if source[offset:offset + len(before) // 2] != bytes.fromhex(before) or offset % 4:
        raise ValueError('render hook mismatch')
    shim = asm.label_addr(program, base, 'render_xy', symbols)
    write(offset, bytes.fromhex('7847c046') + struct.pack('<III', 0xE59FC000, 0xE12FFF1C, shim | 1),
          'render hook')

    # 시스템 문자열: 원본 본문(0x86D6B4~, 구간 밖)은 그대로 두고, 번역문만 구간 안(본문 기준 64KB 이내)에 쓴 뒤
    # 오프셋표를 제자리에서 고친다. 코드 참조는 바꿀 필요가 없다.
    new_offsets, written = bytearray(source[SYS_TABLE:SYS_TABLE + SYS_SLOTS * 2]), {}
    for slot, body in sorted(system.items()):
        old = sys_offsets[slot]
        raw = source[SYS_TEXT + old:source.index(0xFF, SYS_TEXT + old)]
        data = (raw[:2] if raw.startswith(b'\xf7') else b'') + rz3.encode(body + '{end}', codes)
        if data not in written:
            at = alloc(len(data), f'system text S{slot:03X}', SYS_TEXT + 0x10000)
            write(at, data, f'system text S{slot:03X}')
            written[data] = at - SYS_TEXT
        struct.pack_into('<H', new_offsets, slot * 2, written[data])
    if system:
        write(SYS_TABLE, bytes(new_offsets), 'system text offsets')
    extents = {}
    for bank in full:
        old_offsets, old_base, _ = banks[bank]
        count = (old_base - old_offsets) // 2
        offsets, data, shared = bytearray(), bytearray(), {}
        for slot in range(count):
            mid = f'{bank:02X}{slot:02X}'
            pointer = old_offsets + slot * 2
            address = old_base + struct.unpack_from('<H', source, pointer)[0]
            raw = bytes.fromhex(original[mid]['raw'])
            if int(original[mid]['offset_addr'], 16) != pointer or int(original[mid]['addr'], 16) != address \
                    or source[address:address + len(raw)] != raw:
                raise ValueError(f'inventory differs from ROM for {mid}')
            encoded = rz3.encode(messages[mid], codes)
            if encoded not in shared:   # 같은 문장(보스 대사 반복 등)은 한 번만 기록하고 오프셋을 공유
                shared[encoded] = len(data)
                data += encoded
            offsets += struct.pack('<H', shared[encoded])
        if len(data) > 0x10000:
            raise ValueError(f'bank {bank:02X} exceeds 16-bit offsets')
        cursor = alloc(count * 2 + len(data), f'dialogue bank {bank:02X}')
        new_base = cursor + count * 2
        extents[bank] = new_base + len(data)
        write(cursor, offsets + data, f'dialogue bank {bank:02X}')
        write(offset_table + bank * 4, struct.pack('<I', ROM_BASE + cursor), 'offset pointer')
        write(text_table + bank * 4, struct.pack('<I', ROM_BASE + new_base), 'text pointer')
    if any(ROM_BASE + a < ROM_BASE + klo or b > khi for a, b in free):
        raise ValueError('allocator left the Korean window')
    pause4_gfx.apply(source, write)   # 서브 화면·타이틀 메뉴 그림 글자(무압축 타일, 제자리)
    if set(source[title_prompt4.TARGET:title_prompt4.TARGET + 0x428C]) != {0xFF}:
        raise ValueError('title prompt target area is not free')
    title_prompt4.apply(source, write)   # 시작 안내(압축 묶음을 빈 조각으로 옮김)
    gameover4.apply(source, write)   # 게임오버
    logo4.apply(source, write)   # 타이틀 로고
    opening4.apply(source, write)   # 오프닝 문단(그림)
    rom = bytes(rom)
    for bank, (offs, tbase, bound) in enumerate(bank_ranges(rom, offset_table, text_table, bank_count)):
        if bank not in full:
            bound = min(bound, DIALOGUE_SPAN[1])   # 마지막 뱅크 경계는 다음 데이터까지 잡히므로 대사 끝에서 자른다
            if (offs, tbase) != banks[bank][:2] or rom[offs:bound] != source[offs:bound]:
                raise ValueError(f'untouched bank {bank:02X} changed')
            continue
        for slot in range((tbase - offs) // 2):
            mid = f'{bank:02X}{slot:02X}'
            start = tbase + struct.unpack_from('<H', rom, offs + slot * 2)[0]
            _, decoded = read_message(rom, start, extents[bank], LEADS, glyphs)
            if decoded != messages[mid]:
                raise ValueError(f'ROM readback mismatch for {mid}')
    for slot, body in system.items():   # 시스템 문자열 되읽기
        start = SYS_TEXT + struct.unpack_from('<H', rom, SYS_TABLE + slot * 2)[0]
        _, decoded = read_message(rom, start, start + 0x400, LEADS, glyphs)
        if not decoded.endswith(body + '{end}'):
            raise ValueError(f'system text S{slot:03X}: ROM readback mismatch')
    out.parent.mkdir(exist_ok=True)
    out.write_bytes(rom)
    done = sum(1 for b in full for _ in range((banks[b][1] - banks[b][0]) // 2))
    print(f'{out}: window {klo:#x}-{khi:#x}, banks {[f"{b:02X}" for b in full]}, {done}/{len(original)} '
          f'messages, {len(extra)} glyphs, free {[hex(b - a) for a, b in free]}, CRC32 {zlib.crc32(rom):08X}')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, default=HERE / 'out/rz4_dev.gba')
    ap.add_argument('--check', action='store_true', help='원고 폭·제어 코드만 검사(롬 배치 생략)')
    args = ap.parse_args()
    if args.check:
        original, messages = load_text()
        print(f'layout OK: {len(messages)}/{len(original)} messages')
    else:
        main(args.out)
