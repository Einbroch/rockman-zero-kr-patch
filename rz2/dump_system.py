"""2편 시스템 문자열 표 덤프 -> ref/rz2_system_inventory.json"""
import json, struct, sys, zlib
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parent
sys.path.insert(0, str(ROOT / 'tools'))
import dump_sequel_text as D
OT, TB = 0x34B6DC, 0x34BC44
src = (ROOT / 'roms/Rockman Zero 2 (Japan).gba').read_bytes()
assert zlib.crc32(src) == 0x9B5C8A4C
glyphs = D.load_map(ROOT / 'tools/rz234_jp_charmap.txt')
n = (TB - OT) // 2
offs = struct.unpack_from(f'<{n}H', src, OT)
ends = sorted(set(offs))
rows = []
bad = 0
for i, o in enumerate(offs):
    s = TB + o
    e = src.index(0xFF, s) + 1
    try:
        raw, text = D.read_message(src, s, e, {0xF0}, glyphs)
    except Exception as ex:
        bad += 1; text = '<<' + src[s:e].hex(' ') + '>>'
    rows.append({'id': f'S{i:03X}', 'addr': hex(s), 'jp': text})
(ROOT / 'ref/rz2_system_inventory.json').write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding='utf-8')
print(n, 'slots, decode failures', bad)
