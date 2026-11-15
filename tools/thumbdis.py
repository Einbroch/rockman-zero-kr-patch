"""Thumb 디스어셈블: python dis.py rom start end"""
import sys, capstone
a=open(sys.argv[1],'rb').read(); s=int(sys.argv[2],16)&0x1ffffff; e=int(sys.argv[3],16)&0x1ffffff
md=capstone.Cs(capstone.CS_ARCH_ARM,capstone.CS_MODE_THUMB)
p=s
while p<e:
    got=False
    for ins in md.disasm(a[p:e],0x08000000+p):
        x=''
        if ins.mnemonic=='ldr' and 'pc' in ins.op_str:
            t=((ins.address+4)&~3)+int(ins.op_str.split('#')[1].rstrip(']'),16)
            x=f'  ; ={int.from_bytes(a[t-0x08000000:t-0x08000000+4],"little"):08x}'
        print(f'{ins.address:08x} {ins.mnemonic} {ins.op_str}{x}'); p=ins.address-0x08000000+ins.size; got=True
    if not got or p<e:
        print(f'{0x08000000+p:08x} .hword {a[p]|a[p+1]<<8:04x}'); p+=2
