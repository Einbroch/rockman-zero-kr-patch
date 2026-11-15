"""IPS 생성: python mkips.py 원본 결과 출력.ips
- 결과가 더 길면 늘어난 영역 전체를 레코드로 쓴다 (0xFF 채움도 RLE로 명시 → 적용 도구의 채움 값에 의존하지 않음)
- 오프셋 0x454F46('EOF')에서 시작하는 레코드는 한 바이트 앞당겨 피한다
- 결과는 다시 적용해 바이트 단위로 검증한다
"""
import sys, os, zlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ips

EOF_OFF = 0x454F46
MAXLEN = 0xFFFF


def diff_runs(a, b):
    n = len(b)
    i = 0
    while i < n:
        if i < len(a) and a[i] == b[i]:
            i += 1
            continue
        j = i
        # 같은 바이트가 6개 넘게 이어지면 끊는다 (레코드 머리 5바이트보다 이득일 때만)
        same = 0
        while j < n:
            if j < len(a) and a[j] == b[j]:
                same += 1
                if same > 6:
                    j -= same - 1
                    break
            else:
                same = 0
            j += 1
        else:
            j = n
        yield i, j
        i = j


def records(a, b):
    out = []
    for s, e in diff_runs(a, b):
        if s == EOF_OFF:
            s -= 1
        p = s
        while p < e:
            q = min(e, p + MAXLEN)
            chunk = b[p:q]
            # 긴 단일 값 구간은 RLE
            if len(chunk) >= 16 and chunk.count(chunk[0]) == len(chunk):
                out.append((p, chunk, True))
            else:
                # 내부의 긴 반복 구간을 RLE 로 분리
                k = p
                while k < q:
                    r = k
                    while r < q and b[r] == b[k]:
                        r += 1
                    if r - k >= 16:
                        out.append((k, b[k:r], True)); k = r
                    else:
                        m = k
                        while m < q:
                            r2 = m
                            while r2 < q and b[r2] == b[m]:
                                r2 += 1
                            if r2 - m >= 16:
                                break
                            m = r2
                        out.append((k, b[k:m], False)); k = m
            p = q
    fixed = []
    for off, data, rle in out:
        if off == EOF_OFF:
            off -= 1; data = b[off:off + 1] + data; rle = False
        fixed.append((off, data, rle))
    return fixed


def write(recs, path):
    with open(path, 'wb') as f:
        f.write(b'PATCH')
        for off, data, rle in recs:
            assert off < 0x1000000 and off != EOF_OFF
            f.write(off.to_bytes(3, 'big'))
            if rle:
                f.write(b'\x00\x00' + len(data).to_bytes(2, 'big') + data[:1])
            else:
                assert len(data) <= MAXLEN
                f.write(len(data).to_bytes(2, 'big') + data)
        f.write(b'EOF')


if __name__ == '__main__':
    a = open(sys.argv[1], 'rb').read()
    b = open(sys.argv[2], 'rb').read()
    recs = records(a, b)
    write(recs, sys.argv[3])
    # 검증: 원본에 적용해 결과와 같아야 한다 (늘어난 영역 채움값을 0으로 가정해도 같아야 함)
    r, tr = ips.parse(open(sys.argv[3], 'rb').read())
    out = bytearray(a) + bytearray(max(0, len(b) - len(a)))   # 0 채움 가정
    for off, data, _ in r:
        out[off:off + len(data)] = data
    ok = bytes(out[:len(b)]) == b and len(out) == len(b)
    print(f'records {len(recs)}, size {os.path.getsize(sys.argv[3])}, verify {"OK" if ok else "FAIL"}, crc {zlib.crc32(b):08x}')
    sys.exit(0 if ok else 1)
