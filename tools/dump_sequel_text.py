"""록맨 제로 2~4 일본판의 대사 뱅크를 메시지 ID 별로 추출한다."""

import argparse
import json
import re
import struct
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
GBA_BASE = 0x08000000
# CRC32(일본판), 오프셋 포인터표, 본문 포인터표, 뱅크 수
TITLES = {
    2: (0x9B5C8A4C, 0x34E0A8, 0x34E0F8, 20),
    3: (0x5A2C41A9, 0x3767B8, 0x376808, 20),
    4: (0xECE42D0E, 0x870C74, 0x870CCC, 22),
}
ARGUMENT_CONTROLS = {0xF3, 0xF4, 0xF5, 0xF6}


def load_map(path):
    glyphs = {}
    for line in path.read_text(encoding='utf-8').splitlines():
        if line.startswith('#') or not line:
            continue
        code, glyph = line.split('=', 1)
        glyphs[bytes.fromhex(code.zfill(len(code) + len(code) % 2))] = glyph
    return glyphs


def encode_message(text, glyphs):
    inverse = {glyph: raw for raw, glyph in glyphs.items()}
    inverse.update({'\n': b'\xFC', '{end}': b'\xFF'})
    encoded = bytearray()
    for token in re.findall(r'\{[^{}]+\}|.', text, flags=re.DOTALL):
        if token in inverse:
            encoded.extend(inverse[token])
        elif token.startswith('{X'):
            encoded.extend(bytes.fromhex(token[2:-1]))
        elif token.startswith('{'):
            encoded.extend(bytes.fromhex(token[1:-1].replace(':', '')))
        else:
            raise ValueError(f'unmapped character {token!r}')
    return encoded.hex(' ')


def bank_ranges(rom, offset_table, text_table, count):
    offsets = struct.unpack_from(f'<{count}I', rom, offset_table)
    bases = struct.unpack_from(f'<{count}I', rom, text_table)
    for table, base in zip(offsets, bases):
        table -= GBA_BASE
        base -= GBA_BASE
        size = base - table
        if not 0 <= table < base < len(rom) or size % 2 or size > 512:
            raise ValueError(f'invalid message table at {table:#x}')
        following = [address - GBA_BASE for address in offsets if address > base + GBA_BASE]
        yield table, base, min(following + [len(rom), base + 0x10000])


def read_message(rom, start, bound, leads, glyphs):
    cursor = start
    text = []
    while cursor < bound:
        code = rom[cursor]
        width = 2 if code in leads or code in ARGUMENT_CONTROLS else 1
        if cursor + width > bound:
            break
        raw = rom[cursor:cursor + width]
        cursor += width
        if code in ARGUMENT_CONTROLS:
            text.append(f'{{{code:02X}:{raw[1]:02X}}}')
        elif code == 0xFC:
            text.append('\n')
        elif code == 0xFF:
            text.append('{end}')
            encoded = rom[start:cursor].hex(' ')
            decoded = ''.join(text)
            if encode_message(decoded, glyphs) != encoded:
                raise ValueError(f'round trip failed at {start:#x}')
            return encoded, decoded
        elif code >= 0xF1 and code not in leads:
            text.append(f'{{{code:02X}}}')
        else:
            text.append(glyphs.get(raw, '{X' + raw.hex().upper() + '}'))
    raise ValueError(f'message at {start:#x} exceeds its bounds ({bound:#x})')


def extract(rom, title, glyphs):
    _, offset_table, text_table, count = TITLES[title]
    output = {}
    for bank, (table, base, end) in enumerate(bank_ranges(rom, offset_table, text_table, count)):
        slots = struct.unpack_from(f'<{(base - table) // 2}H', rom, table)
        positions = sorted(set(slots))
        if base + positions[-1] >= end:
            raise ValueError(f'bank {bank:02X} points outside its text range')
        ends = dict(zip(positions, [base + position for position in positions[1:]] + [end]))
        leads = {0xF0}
        decoded = {}
        for slot, position in enumerate(slots):
            if position not in decoded:
                decoded[position] = read_message(rom, base + position, ends[position], leads, glyphs)
            raw, text = decoded[position]
            output[f'{bank:02X}{slot:02X}'] = {
                'addr': f'{base + position:#x}', 'offset_addr': f'{table + slot * 2:#x}',
                'raw': raw, 'text': text,
            }
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('title', type=int, nargs='+', choices=TITLES)
    args = parser.parse_args()
    glyphs = load_map(Path(__file__).with_name('rz234_jp_charmap.txt'))
    for title in args.title:
        source = (ROOT / 'roms' / f'Rockman Zero {title} (Japan).gba').read_bytes()
        expected_jp = TITLES[title][0]
        if zlib.crc32(source) != expected_jp:
            raise ValueError(f'RZ{title} Japanese ROM CRC mismatch')
        jp = extract(source, title, glyphs)
        result = {
            'title': title, 'source_crc32': f'{expected_jp:08x}',
            'messages': [{'id': key, 'jp': jp[key]} for key in jp],
        }
        out = ROOT / 'ref' / f'rz{title}_text_inventory.json'
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(f'RZ{title} {len(jp)} slots: {out}')

if __name__ == '__main__':
    main()
