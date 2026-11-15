"""록맨 제로 대사 뱅크 디코더/인코더 (일본판 형식).
메시지 id = (bank<<8 | idx); 주소 = textbase[bank] + u16(offtab[bank] + idx*2)
바이트: <0xF0 글자, F0 xx = 글자 0xF0+xx, F1/F2 색, F3~F8 인수 1, F9·FA·FB 인수 0, FC 줄바꿈, FD~FF 끝/구분.
"""
import struct, json, sys, re

def load_charmap(path):
    dec = {}; enc = {}
    for line in open(path, encoding='utf-8'):
        line = line.rstrip('\n')
        if not line or line.startswith('#'): continue
        k, v = line.split('=', 1)
        c = int(k, 16)
        if v == '' or v in enc:
            continue
        dec[c] = v; enc[v] = c
    return dec, enc

CTRL1 = {0xF3, 0xF4, 0xF5, 0xF6, 0xF7, 0xF8}
NAMES = {0xF1: 'c0', 0xF2: 'c1', 0xF9: 'name', 0xFA: 'fa', 0xFB: 'fb', 0xFC: 'n', 0xFD: 'fd', 0xFE: 'fe', 0xFF: 'end'}

def decode(data, dec):
    out = []; i = 0
    while i < len(data):
        b = data[i]
        if b < 0xF0:
            c = b; i += 1
        elif b == 0xF0:
            c = 0xF0 + data[i+1]; i += 2
        elif b in CTRL1:
            out.append('{%02X:%02X}' % (b, data[i+1])); i += 2; continue
        else:
            out.append('\n' if b == 0xFC else '{%s}' % NAMES[b]); i += 1; continue
        out.append(dec.get(c, '{X%03X}' % c))
    return ''.join(out)

def encode(text, enc):
    out = bytearray(); i = 0
    rev = {v: k for k, v in NAMES.items()}
    while i < len(text):
        ch = text[i]
        if ch == '\n': out.append(0xFC); i += 1; continue
        if ch == '{':
            j = text.index('}', i); t = text[i+1:j]; i = j + 1
            m = re.fullmatch(r'([0-9A-F]{2}):([0-9A-F]{2})', t)
            if m: out += bytes([int(m[1], 16), int(m[2], 16)]); continue
            m = re.fullmatch(r'X([0-9A-F]{3})', t)
            if m: c = int(m[1], 16)
            elif t in rev: out.append(rev[t]); continue
            else: raise ValueError('bad tag ' + t)
        else:
            if ch not in enc: raise ValueError(f'unmapped {ch!r}')
            c = enc[ch]; i += 1
        if c < 0xF0: out.append(c)
        else: out += bytes([0xF0, c - 0xF0])
    return bytes(out)

def banks(rom, offtab_tbl, base_tbl, nbanks):
    res = []
    for b in range(nbanks):
        ot = struct.unpack_from('<I', rom, offtab_tbl + 4*b)[0] - 0x08000000
        tb = struct.unpack_from('<I', rom, base_tbl + 4*b)[0] - 0x08000000
        n = (tb - ot) // 2 if tb > ot else None
        res.append((ot, tb, n))
    return res
