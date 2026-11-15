"""오른쪽 이동 + 공격 + 주기적 점프로 스테이지 진행. 상태 저장 이름을 넘긴다."""
import sys, os, hashlib
sys.path.insert(0, os.path.dirname(__file__)); import rt
from PIL import Image
def run(start_state, out_prefix, steps=40, shot_every=4):
    rt.call('load_state', {'path': rt.RT + '/' + start_state})
    ps = []
    for i in range(steps):
        rt.call('set_input', {'buttons': ['right', 'b'] if i % 2 else ['right']})
        rt.call('step', {'frames': 15})
        if i % 4 == 1:
            rt.call('set_input', {'buttons': ['right', 'a']}); rt.call('step', {'frames': 14})
        if i % shot_every == 0:
            ps.append(rt.shot(f'{out_prefix}_{i:03d}'))
    rt.call('set_input', {'buttons': []}); rt.call('step', {'frames': 2})
    rt.call('save_state', {'path': rt.RT + f'/{out_prefix}.mss'})
    rt.sheet(ps[-10:], rt.RT + f'/{out_prefix}_sheet.png', cols=5)
if __name__ == '__main__':
    run(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 40)
