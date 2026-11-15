"""런타임 도우미: emuc 위에 얹은 짧은 함수들."""
import subprocess, json, time, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RT = os.path.join(ROOT, 'scratch', 'rt').replace(os.sep, '/')
def call(t, a=None):
    r = subprocess.run(['python', os.path.join(ROOT, 'tools', 'emuc.py'), 'call', t, json.dumps(a or {})], capture_output=True, text=True, encoding='utf-8')
    return r.stdout
def status():
    return json.loads(call('status'))
def launch(rom, name):
    call('launch', {'content_path': rom.replace(os.sep, '/'), 'system': 'gba', 'name': name, 'replace': True}); time.sleep(6)
    call('pause')
def shot(name):
    p = f'{RT}/{name}.png'; call('screenshot', {'save_path': p}); return p
def step(n): call('step', {'frames': n})
def tap(btn, after=0): call('tap', {'buttons': [btn], 'after_frames': after})
def to_newgame():
    """부팅 -> 타이틀 -> はじめから 직후 (원본·패치 공통 입력열)"""
    call('run_frames', {'n': 1250}); call('pause'); step(300)
    tap('start', 60); tap('start', 30)
def sheet(paths, out, cols=4):
    from PIL import Image
    ims = [Image.open(p) for p in paths]
    rows = (len(ims) + cols - 1) // cols
    o = Image.new('RGB', (cols * 244, rows * 164))
    for k, im in enumerate(ims):
        o.paste(im, ((k % cols) * 244, (k // cols) * 164))
    o.save(out); return out
def save(name):
    call('resume'); call('pause')
    return call('save_state', {'path': f'{RT}/{name}.mss'})
def load(name):
    call('resume'); call('pause')
    return call('load_state', {'path': f'{RT}/{name}.mss'})
