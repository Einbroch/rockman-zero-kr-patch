import sys,struct,json,re,os
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,os.path.join(HERE,'..','tools')); import rztext
rom=open(os.path.join(HERE,'..','roms','Rockman Zero (Japan).gba'),'rb').read()
dec,enc=rztext.load_charmap(os.path.join(HERE,'charmap_jp.txt'))
B=[]
for b in range(19):
    ot=struct.unpack_from('<I',rom,0x2bad84+4*b)[0]-0x08000000; tb=struct.unpack_from('<I',rom,0x2badd0+4*b)[0]-0x08000000
    B.append((ot,tb))
ends=sorted(set([x for p in B for x in p]+[0x2c3984]))
out=[];bad=0;unk={}
for b,(ot,tb) in enumerate(B):
    n=(tb-ot)//2
    offs=[struct.unpack_from('<H',rom,ot+2*i)[0] for i in range(n)]
    bend=min(e for e in ends if e>tb)
    for i,o in enumerate(offs):
        s=tb+o
        nxt=[tb+x for x in offs if tb+x>s]; e=min(nxt) if nxt else bend
        raw=rom[s:e]
        t=rztext.decode(raw,dec)
        if rztext.encode(t,enc)!=raw: bad+=1
        t=t[:t.index('{end}')+5]   # 끝 표시 뒤 채움 제거 (모든 메시지에 {end} 정확히 1개)
        for m in re.findall(r'\{X([0-9A-F]{3})\}',t): unk[m]=unk.get(m,0)+1
        out.append({'id':f'{b:02X}{i:02X}','addr':hex(s),'len':len(raw),'jp':t})
# 시스템 문자열 뱅크 (메뉴·미션명·엘프·스태프 등): 오프셋표 0x2b8ef0, 본문 0x2b92de, 503개
SYS_OT,SYS_BASE=0x2b8ef0,0x2b92de
for i in range((SYS_BASE-SYS_OT)//2):
    s=SYS_BASE+struct.unpack_from('<H',rom,SYS_OT+2*i)[0]; e=s
    while rom[e]!=0xFF:
        e+= 2 if rom[e] in (0xF0,0xF3,0xF4,0xF5,0xF6,0xF7,0xF8) else 1
    raw=rom[s:e+1]; t=rztext.decode(raw,dec)
    if rztext.encode(t,enc)!=raw: bad+=1
    for m in re.findall(r'\{X([0-9A-F]{3})\}',t): unk[m]=unk.get(m,0)+1
    out.append({'id':f'S{i:03X}','addr':hex(s),'len':len(raw),'jp':t})
json.dump(out,open(os.path.join(HERE,'script_jp.json'),'w',encoding='utf-8'),ensure_ascii=False,indent=1)
with open(os.path.join(HERE,'script_jp.txt'),'w',encoding='utf-8') as f:
    for m in out: f.write(f"### {m['id']} {m['addr']}\n{m['jp']}\n")
print(len(out),'msgs, roundtrip fail',bad,'unk',unk)
