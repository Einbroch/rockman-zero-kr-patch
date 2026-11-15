"""3편 시스템 문자열 번역(rz3/ko_sys/*.txt) 로더와 배치 검사.

파일 형식은 1편과 같다: `### S번호` 머리줄 + 본문(끝의 {end}는 있어도 되고 없어도 된다).
- 원문이 완전히 같은 칸은 번역 하나를 공유한다.
- 원문이 {F7}x 로 시작하면 screen_text.apply 가 원본 앞 2바이트를 그대로 붙이므로 번역문에서는 뺀다
  (번역문에 적어 두면 여기서 원문과 같은지 확인한 뒤 떼어 낸다).
- 검사: 제어 코드 열(색 F1/F2, F7+인수, 줄바꿈 수는 제외)이 원문과 같을 것,
  줄 폭이 묶음별 원문 최대 폭 이하, 줄 수가 묶음별 원문 최대 줄 수 이하.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / 'rz1'))
import build as rz1  # noqa: E402  (parse_txt)

TOKENS = re.compile(r'\{[^{}]+\}|.', re.DOTALL)
THIN = chr(0x2002)   # 4px 공백 (build_dialogue.make_font 가 만든다)


def thin_spaces(text):
    """단어 사이 홑공백만 4px 공백으로. 줄 머리·꼬리 공백과 두 칸 이상 연속 공백(들여쓰기·줄 맞춤)은 그대로."""
    # {F7} 바로 뒤 글자는 인수 바이트라 건드리지 않는다
    text = text.replace('{F7} ', '{F7}\x00ARG')
    text = re.sub(r'(?<=[^ \n]) (?=[^ \n])', THIN, text)
    return text.replace('{F7}\x00ARG', '{F7} ')

# 묶음: (첫 칸, 끝 칸, 이름). 폭·줄 수 한도는 묶음 안 원문 최댓값 (실기 확인 전 잠정값)
GROUPS = [
    (0x000, 0x00B, 'misc'), (0x00C, 0x02E, 'digits_level'), (0x02F, 0x03D, 'area'), (0x03E, 0x04B, 'briefing'),
    (0x04C, 0x0AE, 'elf_name'), (0x0AF, 0x0C7, 'elf_menu'), (0x0C8, 0x128, 'elf_talk'),
    (0x129, 0x14B, 'equip'), (0x14C, 0x176, 'feed'), (0x177, 0x18F, 'save'), (0x190, 0x19B, 'place'),
    (0x19C, 0x1CE, 'ex_name'), (0x1CF, 0x1DF, 'ex_desc'), (0x1E0, 0x21B, 'title_link'),
    (0x21C, 0x226, 'credits'), (0x227, 0x2C1, 'chip'), (0x2C2, 0x2CF, 'files'), (0x2D0, 0x2D5, 'pickup'),
    (0x2D6, 0x3D4, 'gallery'), (0x3D5, 0x3E1, 'data'), (0x3E2, 0x447, 'minigame'),
]
# 화면 실측으로 정한 개별 한도(px). 없으면 묶음 한도.
# 엘프 이름 칸: 일본어 최대 5자(40px)지만 2편과 같은 화면 배치라 48px(한글 4자)로 둔다 — 실기 확인 필요
ID_LIMITS = {i: 48 for i in range(0x04C, 0x0AF)}


def width(line):
    w = 0
    for tok in TOKENS.findall(line):
        if tok.startswith('{'):
            continue
        w += 12 if '가' <= tok <= '힣' else 4 if tok == THIN else 8
    return w


def control_seq(text):
    """색·F7(+인수 글자)·그 밖 제어의 순서. 줄바꿈과 {end} 는 뺀다."""
    out = []
    toks = TOKENS.findall(text)
    i = 0
    while i < len(toks):
        t = toks[i]
        if t == '{F7}':
            out.append('F7' + (toks[i + 1] if i + 1 < len(toks) else ''))
            i += 2
            continue
        if t.startswith('{') and t != '{end}':
            out.append(t)
        i += 1
    return out


def lines_of(text):
    return re.sub(r'\{end\}$', '', text).split('\n')


def group_limits(jp):
    lim = {}
    for a, b, name in GROUPS:
        w = n = 0
        for i in range(a, b + 1):
            t = jp.get(i)
            if t is None:
                continue
            ls = lines_of(t)
            n = max(n, len(ls))
            w = max(w, *(width(l) for l in ls))
        for i in range(a, b + 1):
            lim[i] = (ID_LIMITS.get(i, w), n, name)
    return lim


def load(existing):
    """existing: screen_text 의 기존 {칸: 번역}. -> 추가 번역 {칸: 번역(끝 {end} 없음)}"""
    inv = json.loads((ROOT / 'ref/rz3_system_inventory.json').read_text(encoding='utf-8'))
    jp = {int(r['id'][1:], 16): r['jp'] for r in inv}
    explicit = {}
    for path in sorted((HERE / 'ko_sys').glob('*.txt')):
        for sid, text in rz1.parse_txt(path.read_text(encoding='utf-8-sig')):
            slot = int(sid[1:], 16)
            if slot not in jp or slot in explicit or slot in existing:
                raise ValueError(f'{path.name}: unknown, repeated or already-built slot {sid}')
            text = thin_spaces(text)
            explicit[slot] = text if text.endswith('{end}') else text + '{end}'
    # 원문이 같은 칸 공유
    by_jp = {}
    for slot, text in explicit.items():
        by_jp.setdefault(jp[slot], set()).add(text)
    out = dict(explicit)
    for slot, src in jp.items():
        if slot in out or slot in existing:
            continue
        cand = by_jp.get(src)
        if cand and len(cand) == 1:
            out[slot] = next(iter(cand))
    # 검사
    lim = group_limits(jp)
    errors = []
    for slot, text in sorted(out.items()):
        src = jp[slot]
        if control_seq(text) != control_seq(src):
            errors.append(f'S{slot:03X}: control sequence {control_seq(text)} != {control_seq(src)}')
        w, n, name = lim[slot]
        ls = lines_of(text)
        if len(ls) > n:
            errors.append(f'S{slot:03X} [{name}]: {len(ls)} lines > {n}')
        for k, l in enumerate(ls):
            if width(l) > w:
                errors.append(f'S{slot:03X} [{name}] line {k}: {width(l)}px > {w}px  {l!r}')
    if errors:
        raise ValueError('system text layout:\n  ' + '\n  '.join(errors[:400])
                         + (f'\n  ... {len(errors) - 400} more' if len(errors) > 400 else ''))
    # apply() 형식으로: {end} 제거, 원본이 {F7}x 로 시작하면 그 2토큰 제거
    result = {}
    for slot, text in out.items():
        body = text[:-5]
        if jp[slot].startswith('{F7}'):
            toks = TOKENS.findall(body)
            if toks[:2] != TOKENS.findall(jp[slot])[:2]:
                raise ValueError(f'S{slot:03X}: leading F7 prefix differs')
            body = ''.join(toks[2:])
        result[slot] = body
    missing = sorted(set(jp) - set(out) - set(existing))
    return result, missing
