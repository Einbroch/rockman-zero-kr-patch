"""번역 파일 문자열 치환: python repl.py 파일 <<< 'old=>new' 줄들 (각 old 는 정확히 1회 이상 있어야 함)"""
import sys
p = sys.argv[1]
s = open(p, encoding='utf-8').read()
for line in sys.stdin.read().split('\n'):
    if '=>' not in line:
        continue
    a, b = line.split('=>', 1)
    a = a.replace('⏎', chr(10)); b = b.replace('⏎', chr(10))
    if a not in s:
        sys.exit(f'not found: {a!r}')
    s = s.replace(a, b)
open(p, 'w', encoding='utf-8').write(s)
print('ok')
