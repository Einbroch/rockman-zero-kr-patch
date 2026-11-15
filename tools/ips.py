"""IPS 적용·분석 도구. 사용: python ips.py apply src.gba patch.ips out.gba | info patch.ips"""
import sys

def parse(data):
    assert data[:5] == b'PATCH', 'not IPS'
    p = 5; recs = []; trunc = None
    while True:
        off = int.from_bytes(data[p:p+3], 'big'); p += 3
        if off == 0x454F46 and p >= len(data) - 3:
            if p < len(data):
                trunc = int.from_bytes(data[p:p+3], 'big')
            break
        size = int.from_bytes(data[p:p+2], 'big'); p += 2
        if size == 0:
            n = int.from_bytes(data[p:p+2], 'big'); v = data[p+2]; p += 3
            recs.append((off, bytes([v]) * n, True))
        else:
            recs.append((off, data[p:p+size], False)); p += size
    return recs, trunc

def apply(src, recs, trunc):
    out = bytearray(src)
    for off, b, _ in recs:
        if off + len(b) > len(out):
            out.extend(b'\xff' * (off + len(b) - len(out)))
        out[off:off+len(b)] = b
    if trunc is not None:
        del out[trunc:]
    return bytes(out)

if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'apply':
        src = open(sys.argv[2], 'rb').read()
        recs, tr = parse(open(sys.argv[3], 'rb').read())
        out = apply(src, recs, tr)
        open(sys.argv[4], 'wb').write(out)
        print(f'{len(recs)} records, out size {len(out):#x}')
    elif cmd == 'info':
        recs, tr = parse(open(sys.argv[2], 'rb').read())
        tot = sum(len(b) for _, b, _ in recs)
        print(f'records {len(recs)}, bytes {tot}, max end {max(o+len(b) for o,b,_ in recs):#x}, trunc {tr}')
