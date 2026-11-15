"""록맨 제로 1 한글패치 빌드.

입력: roms/Rockman Zero (Japan).gba (CRC ff2a67b1), rz1/ko/*.json 번역, external/fonts/Galmuri11.bdf
출력: rz1/out/rz1_kr.gba
"""
import sys, os, json, struct, zlib, re, argparse
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import asm, kfont, rztext
import gfx_labels, gfxtext
import logo_rz1

JP_ROM = os.path.join(ROOT, 'roms', 'Rockman Zero (Japan).gba')
JP_CRC = 0xff2a67b1
NEW_BASE = 0x800000          # 확장 영역 (ROM 16MB)
CODE_AT = 0x800000
GTAB_AT = 0x801000
OFFTAB_PTRS = 0x2bad84       # 뱅크별 오프셋표 포인터 19개
TEXT_PTRS = 0x2badd0         # 뱅크별 본문 기준 포인터 19개
NBANKS = 19
HOOK_RENDER = 0x0bc3e8
HOOK_UPLOAD = 0x0bc094
RESULT_STATUS_TABLE = 0x2C62C8
RESULT_TITLE_TABLE = 0x29F9F0
QUEUE_TEXT = 0x080BC1D0
RESULT_WORDING = ('실패', '성공')
RESULT_STATUS_CODES = {'실': 0xBC, '패': 0xAF, '성': 0xBE, '공': 0xB2}
RESULT_TITLES = ('헌터', '전사', '용사', '영웅', '구세주', '신', '평화주의', '질풍', '파괴신',
                 '검호', '저격수', '엘프중독', '굼벵이', '태엽인형', '고물', '고철', '무능',
                 '수집가', '패배자', '마스터')

# 1바이트 글리프: 원본과 같은 자리(숫자 0x01~0x0A, 영문 0x0B~0x3E)는 유지 — 런타임 숫자 문자열 호환
SINGLE = {' ': 0x00}
for i, ch in enumerate('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'):
    SINGLE[ch] = 0x01 + i
EXTRA = '.,!?~-:/()「」\'"・★☆%&+=‥…<>*_[]♪'   # 0x40~
for i, ch in enumerate(EXTRA):
    SINGLE[ch] = 0x40 + i
SINGLE['　'] = 0x7F            # 8px 공백 (줄 맞춤용)
CTRL = {'n': 0xFC, 'c0': 0xF1, 'c1': 0xF2, 'name': 0xF9, 'fa': 0xFA, 'fb': 0xFB, 'fd': 0xFD, 'fe': 0xFE, 'end': 0xFF}


def fail(msg):
    print('BUILD FAIL:', msg)
    sys.exit(1)


def point_result_call(rom, offset, expected):
    if rom[offset:offset + 4] != bytes.fromhex(expected):
        fail(f'mission result call mismatch or overlapping write at {offset:#x}')
    draw_address = 0x08000000 + offset
    call = asm.assemble(f'bl #{QUEUE_TEXT:#x}', draw_address)
    upper, lower = struct.unpack('<HH', call)
    displacement = ((upper & 0x7FF) << 12) | ((lower & 0x7FF) << 1)
    if displacement & 0x400000:
        displacement -= 0x800000
    if upper >> 11 != 0x1E or lower >> 11 != 0x1F or draw_address + 4 + displacement != QUEUE_TEXT:
        fail('mission result branch target mismatch')
    rom[offset:offset + 4] = call


def write_result_text(rom, source, start, encode_char):
    """결과 상태는 고정폭 한 줄로, 코드네임은 가변폭으로 표시한다."""
    if rom[RESULT_STATUS_TABLE:RESULT_STATUS_TABLE + 8] != bytes.fromhex('c41e0d08bc1e0d08'):
        fail('mission result status table mismatch or overlapping write')
    table_end = RESULT_TITLE_TABLE + 4 * len(RESULT_TITLES)
    if rom[RESULT_TITLE_TABLE:table_end] != source[RESULT_TITLE_TABLE:table_end]:
        fail('mission result codename table overlaps another build write')
    for offset, expected in ((0xC050C, 'fbf7c4fe'), (0xC0528, 'fbf7b6fe')):
        point_result_call(rom, offset, expected)
    # 결과 값은 x=128에서 시작한다. 8px 글꼴 두 칸을 첫 타일 행에만 그린다.
    if rom[0xC044E:0xC0450] != bytes.fromhex('0f21'):
        fail('mission result status x-coordinate instruction mismatch')
    rom[0xC044E:0xC0450] = bytes.fromhex('1021')
    # 비밀 칭호 「마스터」를 고르는 별도 분기도 같은 번역을 사용한다.
    if rom[0xC04DA:0xC04DE] != bytes.fromhex('074814e0') or rom[0xC04F8:0xC04FC] != bytes.fromhex('d01e0d08'):
        fail('mission result direct codename pointer mismatch or overlapping write')
    end = (start + 3) & ~3
    # Select the fixed-height Korean font only for the result screen caller.
    loader_at = end
    font_at = loader_at + 0x40
    end = font_at + 0x800
    if end > len(rom) or rom[loader_at:end] != b'\xFF' * (end - loader_at):
        fail('mission result font overlaps another build write')
    loader_source = """
        mov r0, lr
        ldr r1, result_return
        cmp r0, r1
        ldr r0, original_font
        bne copy_font
        ldr r0, result_font
    copy_font:
        ldr r2, bgcnt
        ldrh r2, [r2]
        movs r1, #0xc
        ands r1, r2
        lsls r1, r1, #12
        ldr r2, destination
        adds r1, r1, r2
        movs r2, #0x80
        lsls r2, r2, #2
        svc #0xc
        bx lr
        .align 2
    result_return: .word 0x080C01DD
    original_font: .word 0x080D169C
    result_font: .word RESULT_FONT
    bgcnt: .word 0x02004F34
    destination: .word 0x06007000
    """
    loader_base = 0x08000000 + loader_at
    loader = asm.assemble(loader_source, loader_base, {'RESULT_FONT': 0x08000000 + font_at})
    if len(loader) > font_at - loader_at or asm.check_thumb1(loader[:-20], loader_base):
        fail('invalid mission result font loader')
    if rom[0xBBFDC:0xBBFE4] != source[0xBBFDC:0xBBFE4]:
        fail('mission result font loader hook overlaps another build write')
    rom[0xBBFDC:0xBBFE4] = bytes.fromhex('004b1847') + struct.pack('<I', loader_base | 1)
    rom[loader_at:loader_at + len(loader)] = loader
    rom[font_at:end] = source[0xD169C:0xD1E9C]
    for ch, code in RESULT_STATUS_CODES.items():
        width, bitmap = gfxtext.text_bitmap(ch)
        if width > 8:
            fail(f'mission result glyph {ch!r} is too wide')
        tile = [[0] * 8 for _ in range(8)]
        for y, row in enumerate(bitmap):
            for x, ink in enumerate(row[:-1] if width == 8 else row):
                if ink:
                    tile[y + 1][x + 1] = 2
        for y, row in enumerate(bitmap):
            for x, ink in enumerate(row):
                if ink:
                    tile[y][x] = 1
        gfxtext.put_px(rom, font_at, code - 0xA0, tile)
    for table, strings in ((RESULT_STATUS_TABLE, RESULT_WORDING), (RESULT_TITLE_TABLE, RESULT_TITLES)):
        for index, wording in enumerate(strings):
            if table == RESULT_STATUS_TABLE:
                encoded = bytes(RESULT_STATUS_CODES[ch] for ch in wording) + b'\x00'
            else:
                encoded = b''.join(encode_char(ch) for ch in wording) + b'\xFF'
            limit = end + len(encoded)
            if limit > len(rom) or rom[end:limit] != b'\xFF' * len(encoded):
                fail('mission result text overlaps another build write')
            struct.pack_into('<I', rom, table + index * 4, 0x08000000 + end)
            rom[end:limit] = encoded
            end = limit
    rom[0xC04F8:0xC04FC] = rom[table_end - 4:table_end]
    return end


def parse_txt(t):
    """'### ID' 머리줄 + 본문 형식. 머리줄 외 '#' 줄은 주석."""
    out = []
    cur = None; buf = []
    for line in t.split('\n'):
        m = re.match(r'### (\S+)', line)
        if m:
            if cur: out.append((cur, '\n'.join(buf).rstrip('\n')))
            cur = m[1]; buf = []
        elif cur is not None and not line.startswith('#'):
            buf.append(line)
    if cur: out.append((cur, '\n'.join(buf).rstrip('\n')))
    return out


def load_messages(test=False):
    jp = json.load(open(os.path.join(HERE, 'script_jp.json'), encoding='utf-8'))
    ko = {}
    kodir = os.path.join(HERE, 'ko')
    if os.path.isdir(kodir):
        for fn in sorted(os.listdir(kodir)):
            if fn.endswith('.txt'):
                items = parse_txt(open(os.path.join(kodir, fn), encoding='utf-8').read())
            elif fn.endswith('.json'):
                items = json.load(open(os.path.join(kodir, fn), encoding='utf-8')).items()
            else:
                continue
            if True:
                for k, v in items:
                    if k in ko:
                        fail(f'duplicate translation id {k} in {fn}')
                    ko[k] = v
    test_ids = set()
    if test:   # 실기 시험용 덮어쓰기 (배포 빌드에서는 쓰지 않음)
        tdir = os.path.join(HERE, 'test')
        for fn in sorted(os.listdir(tdir)):
            if fn.endswith('.txt'):
                for k, v in parse_txt(open(os.path.join(tdir, fn), encoding='utf-8').read()):
                    ko[k] = v; test_ids.add(k)
    # 원문이 완전히 같은 메시지는 번역을 공유한다 (번역이 한 곳에만 있어도 됨)
    by_jp = {}
    for m in jp:
        if m['id'] in ko and m['id'] not in test_ids:
            by_jp.setdefault(m['jp'], ko[m['id']])
    for m in jp:
        if m['id'] not in ko and m['jp'] in by_jp:
            ko[m['id']] = by_jp[m['jp']]
    # {Jxxx} = 원본 일본어 폰트 글리프 xxx 를 그대로 (버튼 아이콘 등) -> 사용자 정의 영역 문자
    pua = lambda t: re.sub(r'\{J([0-9A-F]{3})\}', lambda mm: chr(0xE000 + int(mm[1], 16)), t)
    ko = {k: pua(v) for k, v in ko.items()}
    msgs = []
    missing = []
    for m in jp:
        if m['id'] in ko:
            msgs.append((m['id'], ko[m['id']], 'test' if m['id'] in test_ids else 'ko'))
        else:
            missing.append(m['id'])
            msgs.append((m['id'], None, 'missing'))
    return jp, msgs, missing


def tokens(text):
    """번역문 -> 토큰 열: ('ch', 글자) / ('raw', bytes)"""
    i = 0
    while i < len(text):
        c = text[i]
        if c == '\n':
            yield ('raw', bytes([0xFC])); i += 1; continue
        if c == '{':
            j = text.index('}', i); t = text[i+1:j]; i = j + 1
            m = re.fullmatch(r'([0-9A-F]{2}):([0-9A-F]{2})', t)
            if m:
                yield ('raw', bytes([int(m[1], 16), int(m[2], 16)])); continue
            if t in CTRL:
                yield ('raw', bytes([CTRL[t]])); continue
            fail(f'unknown tag {{{t}}} in {text[:40]!r}')
        yield ('ch', c); i += 1


PORTRAIT_W, PORTRAIT_LINES = 160, 4     # 초상화 창: x=72~232, 4줄 (실기 측정 11/12)
PLAIN_W, PLAIN_LINES = 224, 1           # 초상화 없는 통신문 한 줄
CELL_LIMIT = 76                          # 캐시 80칸 - 여유 4


# 시스템 뱅크 묶음: (시작, 끝) -> 한도는 묶음 안 원문 최대 폭·최대 줄 수 (잠정, 화면별 실기 확인 전)
SYS_GROUPS = [(0x000, 0x046), (0x047, 0x05A), (0x05B, 0x0B1), (0x0B2, 0x0B5), (0x0B6, 0x115),
              (0x116, 0x11C), (0x11D, 0x140), (0x141, 0x163), (0x164, 0x175), (0x176, 0x188),
              (0x189, 0x18F), (0x190, 0x1F2), (0x1F3, 0x1F6)]


# 화면 실측으로 정한 개별 한도 (px). 키: 메시지 ID
ID_LIMITS = {
    'S040': 112,   # 컨티뉴 「재도전 남은 횟수」: 문장 x=72, 남은 횟수 숫자 x=184 (11/12 실기)
}


def sys_group_limits(jp):
    lim = {}
    for a, b in SYS_GROUPS:
        w = 0; n = 0
        for i in range(a, b + 1):
            t = jp.get(f'S{i:03X}')
            if t is None:
                continue
            for _, lines in split_pages(t):
                n = max(n, len(lines))
                for l in lines:
                    w = max(w, len(line_items(l)) * 8)
        for i in range(a, b + 1):
            lim[f'S{i:03X}'] = (w, n)
    return lim


def split_pages(text):
    """-> [(초상화 여부, [줄 문자열(태그 포함)])]. {F3:xx} 는 그 페이지부터 초상화."""
    out = []
    por = False
    for seg in re.split(r'\{(?:fd|fe|end)\}', text):
        if re.search(r'\{F3:..\}', seg):
            por = True
        out.append((por, seg.split('\n')))
    return out[:-1] if text.endswith('{end}') else out


def line_items(line):
    """줄 -> [(글자, 색)] (태그 제거, 색 추적)"""
    items = []
    color = 0
    for m in re.finditer(r'\{([^}]*)\}|(.)', line, re.S):
        if m[1] is not None:
            if m[1] == 'c1': color = 1
            elif m[1] == 'c0': color = 0
            continue
        items.append((m[2], color))
    return items


def check_layout(msgs, jp, widths, qinfo):
    viol = []
    slim = sys_group_limits(jp)
    for mid, t, kind in msgs:
        if t is None:
            continue
        jp_pages = split_pages(jp[mid])
        for pi, (por, lines) in enumerate(split_pages(t)):
            cells = set()
            if mid[0] == 'S':
                gw, gn = slim[mid]
                limits = [ID_LIMITS.get(mid, gw)] * 8
                maxl = gn
            else:
                limits = None
                maxl = PORTRAIT_LINES if por else PLAIN_LINES
            if len(lines) > maxl:
                viol.append((kind, mid, f'page {pi}: {len(lines)} lines > {maxl}'))
            for li, l in enumerate(lines):
                items = line_items(l)
                w = sum(widths.get(ch, 0) for ch, _ in items)
                if limits is not None:
                    lim = limits[li] if li < len(limits) else 0
                else:
                    lim = PORTRAIT_W if por else PLAIN_W
                if w > lim:
                    viol.append((kind, mid, f'page {pi} line {li}: {w}px > {lim}px  {l!r}'))
                # 칸 시뮬레이션: 4px 조각 두 개씩
                qs = []
                for ch, col in items:
                    q0, n, rep = qinfo.get(ch, (0, 0, 0))
                    for k in range(n):
                        qs.append(((q0 if rep else q0 + k) | (col << 15)))
                if len(qs) % 2:
                    qs.append(0)
                for k in range(0, len(qs), 2):
                    cells.add((qs[k], qs[k + 1] & 0x7FFF))
            if len(cells) > CELL_LIMIT:
                viol.append((kind, mid, f'page {pi}: {len(cells)} distinct cells > {CELL_LIMIT}'))
    return viol


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--test', action='store_true')
    ap.add_argument('--out', default=os.path.join(HERE, 'out', 'rz1_kr.gba'))
    a = ap.parse_args()

    rom = bytearray(open(JP_ROM, 'rb').read())
    if zlib.crc32(rom) != JP_CRC:
        fail('source ROM CRC mismatch')
    src = bytes(rom)
    rom += b'\xff' * (0x1000000 - len(rom))

    jp, msgs, missing = load_messages(a.test)
    if missing:
        fail(f'{len(missing)} messages untranslated (first {missing[:5]})')

    # ---- 글자 수집 -> 한글 음절 번호
    glyphs = kfont.load_bdf(os.path.join(ROOT, 'external', 'fonts', 'Galmuri11.bdf'))
    hangul = set()
    jpglyph = set()
    for _, t, _ in msgs:
        if t is None:
            continue
        for k, v in tokens(t):
            if k == 'ch' and 0xE000 <= ord(v) < 0xE200:
                jpglyph.add(v); continue
            if k == 'ch' and v not in SINGLE:
                if not ('가' <= v <= '힣'):
                    fail(f'unmapped char {v!r} (U+{ord(v):04X})')
                hangul.add(v)
    hangul.update(ch for wording in RESULT_TITLES for ch in wording if ch not in SINGLE)
    for k, v in enumerate(sorted(jpglyph)):
        if 0x68 + k > 0x7E:
            fail('too many original-font glyphs')
        SINGLE[v] = 0x68 + k
    hangul = sorted(hangul)
    hid = {ch: 0x80 + k for k, ch in enumerate(hangul)}
    if 0x80 + len(hangul) > 0x80 + 0x70 * 0xF0:
        fail('too many syllables')

    def enc_char(ch):
        if ch in SINGLE:
            return bytes([SINGLE[ch]])
        k = hid[ch] - 0x80
        return bytes([0x80 + k // 0xF0, k % 0xF0])

    # ---- 글리프 데이터: 조각 0~2 = 빈 조각
    qdat = bytearray(32 * 3)
    nglyph = 0x80 + len(hangul)
    gtab = [0] * nglyph
    widths = {}
    gtab[0x00] = (1 << 31) | (1 << 16) | 0      # 4px 공백
    gtab[0x7F] = (1 << 31) | (2 << 16) | 0      # 8px 공백
    widths[' '] = 4; widths['　'] = 8
    for ch, code in list(SINGLE.items()) + [(c, hid[c]) for c in hangul]:
        if code in (0x00, 0x7F):
            continue
        if 0xE000 <= ord(ch) < 0xE200:      # 원본 폰트 글리프 그대로 (8px)
            import font as jpfont
            px = jpfont.glyph(src, 0x0c969c, ord(ch) - 0xE000)
            q0 = len(qdat) // 32
            qdat += kfont.to_quanta(8, px)
            gtab[code] = q0 | (2 << 16)
            widths[ch] = 8
            continue
        src_ch = ch
        if ord(src_ch) not in glyphs:
            fail(f'font lacks {ch!r}')
        W, px = kfont.render(glyphs, src_ch, 12 if '가' <= ch <= '힣' else None)
        q0 = len(qdat) // 32
        qdat += kfont.to_quanta(W, px)
        gtab[code] = q0 | ((W // 4) << 16)
        widths[ch] = W
    if len(qdat) // 32 >= 0x8000:
        fail('too many quanta')

    # ---- 배치 검사 (번역문 ko 는 위반 시 실패, 개발 참고문 ref 는 경고만)
    qinfo = {}
    for ch, code in SINGLE.items():
        g = gtab[code]
        qinfo[ch] = (g & 0xFFFF, (g >> 16) & 0x7FFF, g >> 31)
    for ch in hangul:
        g = gtab[hid[ch]]
        qinfo[ch] = (g & 0xFFFF, (g >> 16) & 0x7FFF, 0)
    viol = check_layout(msgs, {m['id']: m['jp'] for m in jp}, widths, qinfo)
    report_path = os.path.join(HERE, 'out', 'layout_report.txt')
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, 'w', encoding='utf-8') as f:
        for kind, mid, msg in viol:
            f.write(f'[{kind}] {mid}: {msg}\n')
    hard = [v for v in viol if v[0] == 'ko']
    print(f'layout: {len(hard)} violations in translations, {len(viol) - len(hard)} in test overrides (see {report_path})')
    if hard:
        for v in hard[:15]:
            print('  ', v[1], v[2])
        fail('layout violations')

    # ---- 배치: 코드 -> 글리프표 -> 조각 데이터 -> 대사
    vwf_src = open(os.path.join(HERE, 'asm', 'vwf.s'), encoding='utf-8').read()
    qdat_at = GTAB_AT + (len(gtab) * 4 + 0xF) // 0x10 * 0x10
    text_at = qdat_at + (len(qdat) + 0xF) // 0x10 * 0x10
    sym = {'GTAB_ADDR': 0x08000000 + GTAB_AT, 'QDAT_ADDR': 0x08000000 + qdat_at}
    code = asm.assemble(vwf_src, 0x08000000 + CODE_AT, sym)
    code_end = asm.label_addr(vwf_src, 0x08000000 + CODE_AT, 'L_GTAB', sym) - 0x08000000 - CODE_AT
    bad = asm.check_thumb1(code[:code_end], 0x08000000 + CODE_AT)
    if bad:
        fail(f'non-Thumb1 instructions: {bad[:3]}')
    if CODE_AT + len(code) > GTAB_AT:
        fail('code overflows into glyph table')
    rom[CODE_AT:CODE_AT + len(code)] = code
    rom[GTAB_AT:GTAB_AT + len(gtab) * 4] = b''.join(struct.pack('<I', g) for g in gtab)
    rom[qdat_at:qdat_at + len(qdat)] = qdat
    r_render = asm.label_addr(vwf_src, 0x08000000 + CODE_AT, 'render', sym)
    r_upload = asm.label_addr(vwf_src, 0x08000000 + CODE_AT, 'upload', sym)

    def stub(at, target):
        if at % 4:
            fail('hook not aligned')
        rom[at:at + 8] = bytes.fromhex('004b1847') + struct.pack('<I', target | 1)   # ldr r3,[pc,#0]; bx r3
    stub(HOOK_RENDER, r_render)
    stub(HOOK_UPLOAD, r_upload)

    # ---- 대사 뱅크 재작성
    by_bank = {}
    for (mid, t, kind), j in zip(msgs, jp):
        if mid[0] == 'S':
            by_bank.setdefault('S', []).append((int(mid[1:], 16), t, j))
        else:
            by_bank.setdefault(int(mid[:2], 16), []).append((int(mid[2:], 16), t, j))
    p = text_at
    report = {'ko': 0, 'missing': 0, 'test': 0}
    for _, _, kind in msgs:
        report[kind] += 1
    for b in list(range(NBANKS)) + ['S']:
        items = sorted(by_bank[b])
        n = len(items)
        offtab = p
        base = offtab + n * 2
        base = (base + 1) & ~1
        blob = bytearray()
        offs = []
        for idx, t, j in items:
            offs.append(len(blob))
            if t is None:
                blob += bytes([0xFF])           # 개발 빌드 미번역: 빈 메시지
                continue
            out = bytearray()
            for k, v in tokens(t):
                out += v if k == 'raw' else enc_char(v)
            if not out or out[-1] != 0xFF:
                fail(f'{b}/{idx:03X}: message must end with {{end}}')
            blob += out
        if len(blob) > 0xFFFF:
            fail(f'bank {b} too large')
        for i, o in enumerate(offs):
            struct.pack_into('<H', rom, offtab + i * 2, o)
        rom[base:base + len(blob)] = blob
        if b == 'S':
            # 시스템 뱅크: 코드 리터럴 41곳씩을 새 표로
            for old, new in ((0x082b8ef0, offtab), (0x082b92de, base)):
                pat = struct.pack('<I', old)
                hits = [i for i in range(0, len(src) - 3, 4) if src[i:i+4] == pat]
                if len(hits) != 41:
                    fail(f'system bank literal {old:08x}: expected 41 refs, found {len(hits)}')
                for h in hits:
                    struct.pack_into('<I', rom, h, 0x08000000 + new)
        else:
            struct.pack_into('<I', rom, OFFTAB_PTRS + 4 * b, 0x08000000 + offtab)
            struct.pack_into('<I', rom, TEXT_PTRS + 4 * b, 0x08000000 + base)
        p = (base + len(blob) + 3) & ~3
    if p > 0x1000000:
        fail('ROM full')
    p = write_result_text(rom, src, p, enc_char)

    try:
        graphic_labels = gfx_labels.apply(rom, src)
    except (KeyError, ValueError) as exc:
        fail(f'graphic labels: {exc}')
    try:
        logo_tiles = logo_rz1.apply(rom, src)   # 타이틀 로고 「록맨®제로」
    except ValueError as exc:
        fail(f'title logo: {exc}')

    # ---- 결과
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    open(a.out, 'wb').write(rom)
    info = {'syllables': len(hangul), 'quanta': len(qdat) // 32, 'text_end': hex(p), 'render': hex(r_render),
            'upload': hex(r_upload), 'messages': report, 'graphic_labels': graphic_labels,
            'crc32': f'{zlib.crc32(rom):08x}'}
    json.dump({'widths': widths}, open(os.path.join(HERE, 'out', 'widths.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    print(json.dumps(info, ensure_ascii=False))


if __name__ == '__main__':
    main()
