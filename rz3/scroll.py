"""3편 오프닝 스크롤(S00A)을 미리 합성한 줄 타일로 표시한다.

원래 스크롤은 줄마다 텍스트 출력기(0x080E9BA4)를 부른다. 가변폭 출력기는 셀 캐시(80칸)가
모자라 스크롤 도중 멈추므로, 2편 rz2/screen_text.build_scroll 처럼 호출 두 곳(0x22D86·0x22DB8)을
줄 복사 루틴으로 바꾼다. 3편은 줄이 많아(문단 사이 빈 줄 포함 수십 줄) 모든 줄 타일을 VRAM 에
올릴 수 없으므로, 글자가 있는 줄을 7개 슬롯에 돌려 쓰며 그 줄을 그릴 때 타일 60개를 올린다.
같은 슬롯을 쓰는 두 줄은 GAP(12)행 이상 떨어지게 배정하고, 안 되면 빌드를 멈춘다.
"""

import struct

import gfxtext
import system_text

ROM_BASE = 0x08000000
CALLS = ((0x22D86, 'c6f00dff'), (0x22DB8, 'c6f0f4fe'))   # 원본 bl 0x080E9BA4
HANDLER_SLOT, NATIVE_HANDLER = 0x34D020, 0x08022C7D
VENEER = 0x386160
TILEMAP_TARGET, BG_SHADOW = 0x02030310, 0x02002144
SLOTS, TILE0 = 7, 0x201
GAP = 12   # 화면에 보이는 줄은 최대 11행; 같은 슬롯 두 줄은 이만큼 떨어져야 한다
STRIDE = 60 * 32
TILES_AT, CODE_AT = 0xF68000, 0xF67000

PROGRAM = '''
    push {r4-r7, lr}
    ldr r4, [sp, #20]
    subs r4, r4, r3
    lsls r0, r2, #6
    ldr r1, tilemap_target
    ldr r1, [r1]
    adds r1, r1, r0
rows:
    cmp r4, #0
    ble done
    cmp r3, #LINE_COUNT
    bhs done
    ldr r5, slot_table
    ldrb r5, [r5, r3]
    cmp r5, #0xFF
    beq blank_row
    movs r6, #60
    muls r6, r5, r6
    ldr r7, tile0
    adds r6, r6, r7
    push {r1, r2, r3, r4}
    ldr r0, stride
    muls r0, r3, r0
    ldr r2, line_tiles
    adds r0, r0, r2
    lsls r2, r6, #5
    ldr r3, bg_shadow
    ldrh r3, [r3]
    movs r7, #12
    ands r3, r7
    lsls r3, r3, #12
    ldr r7, vram
    adds r3, r3, r7
    adds r2, r2, r3
    movs r3, #240
copy:
    ldmia r0!, {r4, r7}
    stmia r2!, {r4, r7}
    subs r3, #1
    bne copy
    pop {r1, r2, r3, r4}
    movs r5, #2
half:
    movs r0, #30
cell:
    strh r6, [r1]
    adds r1, #2
    adds r6, #1
    subs r0, #1
    bne cell
    adds r1, #4
    subs r5, #1
    bne half
    b next
blank_row:
    ldr r6, blank_tile
    movs r5, #2
bhalf:
    movs r0, #30
bcell:
    strh r6, [r1]
    adds r1, #2
    subs r0, #1
    bne bcell
    adds r1, #4
    subs r5, #1
    bne bhalf
next:
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
    ldr r1, bg_shadow
    ldrh r1, [r1]
    movs r2, #12
    ands r1, r2
    lsls r1, r1, #12
    ldr r2, blank_dest
    adds r1, r1, r2
    movs r2, #0
    movs r3, #8
clear:
    stmia r1!, {r2}
    subs r3, #1
    bne clear
native:
    pop {r0}
    pop {r3}
    mov lr, r3
    ldr r3, native_scroll
    bx r3
.align 2
tilemap_target: .word TILEMAP_TARGET
bg_shadow: .word BG_SHADOW
vram: .word 0x06000000
blank_dest: .word 0x06004000
native_scroll: .word NATIVE_HANDLER
slot_table: .word SLOT_TABLE
line_tiles: .word LINE_TILES
stride: .word STRIDE
tile0: .word TILE0
blank_tile: .word 0x200
'''


def lines():
    extra, _ = system_text.load({})
    return extra[0x00A].split('\n')


def apply(source, write, asm):
    text = lines()
    jp = system_text.json.loads((system_text.ROOT / 'ref/rz3_system_inventory.json').read_text(encoding='utf-8'))
    original = next(r['jp'] for r in jp if r['id'] == 'S00A')
    if len(text) != original.count('\n') + 1:
        raise ValueError('opening scroll line count differs from the original timing')
    if len(text) > 255:
        raise ValueError('too many scroll lines')
    data, slots, ordinal = bytearray(), bytearray(), 0
    last = [-GAP] * SLOTS
    for line in text:
        line = line.replace(system_text.THIN, ' ').strip()
        surface = [[0] * 240 for _ in range(16)]
        if line:
            width, pixels = gfxtext.text_bitmap(line, 'Galmuri11', height=11)
            left = (240 - width) // 2
            if left < 0:
                raise ValueError(f'opening line exceeds 240px: {line}')
            for y, row in enumerate(pixels, 2):
                surface[y][left:left + width] = row
            free = [k for k in range(SLOTS) if last[k] <= len(slots) - GAP]
            if not free:
                raise ValueError(f'no free scroll slot for line {len(slots)}')
            k = min(free, key=lambda k: last[k])
            last[k] = len(slots)
            slots.append(k)
            ordinal += 1
        else:
            slots.append(0xFF)
        for top in (0, 8):
            for x in range(0, 240, 8):
                tile = bytearray(32)
                gfxtext.put_px(tile, 0, 0, [row[x:x + 8] for row in surface[top:top + 8]])
                data += tile
    if TILE0 + SLOTS * 60 > 0x3C0:
        raise ValueError('scroll slots exceed the tile range')
    slot_at = TILES_AT + len(data)
    write(TILES_AT, data, 'opening scroll line tiles')
    write(slot_at, bytes(slots), 'opening scroll slot table')
    symbols = {'LINE_COUNT': len(text), 'TILEMAP_TARGET': TILEMAP_TARGET, 'BG_SHADOW': BG_SHADOW,
               'NATIVE_HANDLER': NATIVE_HANDLER, 'SLOT_TABLE': ROM_BASE + slot_at,
               'LINE_TILES': ROM_BASE + TILES_AT, 'STRIDE': STRIDE, 'TILE0': TILE0}
    base = ROM_BASE + CODE_AT
    code = asm.assemble(PROGRAM, base, symbols)
    end = asm.label_addr(PROGRAM, base, 'tilemap_target', symbols)
    if asm.check_thumb1(code[:end - base], base):
        raise ValueError('unsupported Thumb instruction in the scroll renderer')
    write(CODE_AT, code, 'opening scroll renderer')
    if source[VENEER:VENEER + 8] != b'\xff' * 8:
        raise ValueError('scroll veneer area is not free')
    write(VENEER, bytes.fromhex('00480047') + struct.pack('<I', base | 1), 'scroll renderer veneer')
    for at, before in CALLS:
        if source[at:at + 4] != bytes.fromhex(before):
            raise ValueError(f'unexpected scroll renderer call at {at:#x}')
        write(at, asm.assemble(f'bl {ROM_BASE + VENEER:#x}', ROM_BASE + at), 'scroll renderer call')
    if struct.unpack_from('<I', source, HANDLER_SLOT)[0] != NATIVE_HANDLER:
        raise ValueError('unexpected scroll command handler')
    init = asm.label_addr(PROGRAM, base, 'init_scroll', symbols)
    write(HANDLER_SLOT, struct.pack('<I', init | 1), 'scroll command handler')
    return len(text), ordinal
