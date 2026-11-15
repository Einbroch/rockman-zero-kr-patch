"""3편 시스템 문자열 표(오프셋표 0x372210, 본문 0x372AA0, 1,096칸)를 한글로 다시 쓴다.

2편 rz2/screen_text.py 와 같은 방식:
- 원본 본문 전체를 NATIVE_COPY(0xF00000)에 그대로 복사하고, 번역한 칸은 그 앞(text_base~)에 새로 쓴다.
  출력기는 0x08F00000 이상을 원래 인코딩, 0x08800000~0x08F00000 을 확장(EC~F0 두 바이트) 인코딩으로 읽는다.
- 새 오프셋표는 text_base = NATIVE_COPY - 0x8000 기준. 안 바꾼 칸은 0x8000 + 원래 오프셋.
- 코드 속 리터럴(오프셋표 77곳, 본문 62곳)을 모두 새 주소로 바꾼다. 오프셋표만 읽는 15곳은
  공통 처리부로 점프해 본문 리터럴을 따로 읽으므로(0x080F57D4 등) 둘 다 바꾸면 된다.
"""

import struct

import system_text

OFFSET_TABLE = 0x372210
TEXT_BASE = 0x372AA0
NATIVE_COPY = 0xF00000
ROM_BASE = 0x08000000
REFERENCES = {OFFSET_TABLE: 77, TEXT_BASE: 62}


def text_end(source):
    count = (TEXT_BASE - OFFSET_TABLE) // 2
    offsets = struct.unpack_from(f'<{count}H', source, OFFSET_TABLE)
    last = max(offsets)
    return TEXT_BASE + last + source[TEXT_BASE + last:].index(0xFF) + 1


def translations():
    extra, _missing = system_text.load({})
    return extra


def apply(source, write, encode):
    end = text_end(source)
    offsets = bytearray(source[OFFSET_TABLE:TEXT_BASE])
    original_text = source[TEXT_BASE:end]
    if len(original_text) > 0x8000:
        raise ValueError('system text does not fit the 0x8000 native window')
    text_base = NATIVE_COPY - 0x8000
    write(NATIVE_COPY, original_text, 'native system text')
    for i, (offset,) in enumerate(struct.iter_unpack('<H', bytes(offsets))):
        struct.pack_into('<H', offsets, 2 * i, 0x8000 + offset)

    cursor = text_base
    encoded = {}
    expected = {}
    for slot, wording in sorted(translations().items()):
        old = struct.unpack_from('<H', source, OFFSET_TABLE + slot * 2)[0]
        raw = original_text[old:original_text.index(0xFF, old)]
        prefix = raw[:2] if raw.startswith(b'\xf7') else b''
        data = prefix + encode(wording + '{end}')
        if data not in encoded:
            if cursor + len(data) > NATIVE_COPY:
                raise ValueError('translated system text overflows into the native copy')
            encoded[data] = cursor - text_base
            write(cursor, data, f'system text S{slot:03X}')
            cursor += len(data)
        struct.pack_into('<H', offsets, slot * 2, encoded[data])
        expected[slot] = encoded[data]

    table = NATIVE_COPY + ((len(original_text) + 3) & ~3)
    write(table, offsets, 'system text offsets')
    # 되읽기: 번역 칸은 자기 번역을, 나머지는 원래 자리(0x8000+옛 오프셋)를 가리켜야 한다
    for slot in range(len(offsets) // 2):
        off = struct.unpack_from('<H', offsets, slot * 2)[0]
        old = struct.unpack_from('<H', source, OFFSET_TABLE + slot * 2)[0]
        if off != expected.get(slot, 0x8000 + old):
            raise ValueError(f'system text S{slot:03X}: offset readback mismatch')
    for old, new in ((OFFSET_TABLE, table), (TEXT_BASE, text_base)):
        literal = struct.pack('<I', ROM_BASE + old)
        hits = [i for i in range(0, 0x400000, 4) if source[i:i + 4] == literal]
        if len(hits) != REFERENCES[old]:
            raise ValueError(f'unexpected reference count for {old:#x}: {len(hits)}')
        for at in hits:
            write(at, struct.pack('<I', ROM_BASE + new), f'system text reference {at:#x}')
    return len(encoded)
