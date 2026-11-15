"""원문 구간 출력: python show.py 시작ID 끝ID"""
import json, sys, os
d = json.load(open(os.path.join(os.path.dirname(__file__), '..', 'rz1', 'script_jp.json'), encoding='utf-8'))
a, b = sys.argv[1], sys.argv[2]
for m in d:
    if a <= m['id'] <= b and (m['id'][0] == 'S') == (a[0] == 'S'):
        print('###', m['id']); print(m['jp'])
