import os,json,sys
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
GAME=r"C:\Program Files (x86)\Steam\steamapps\common\STAR OCEAN - THE LAST HOPE - 4K & Full HD Remaster"
d=open(os.path.join(GAME,"StarOceanTheLastHope.exe"),'rb').read()
secs=json.load(open('pe.json'))['secs']
def r2f(rva):
    for n,va,vsz,ro,rsz in secs:
        if va<=rva<va+max(vsz,rsz): return ro+(rva-va)
md=Cs(CS_ARCH_X86,CS_MODE_64)
a=int(sys.argv[1],16); nbytes=int(sys.argv[2],16); skip=int(sys.argv[3]); lim=int(sys.argv[4])
code=d[r2f(a):r2f(a)+nbytes]
i=0
for ins in md.disasm(code,a):
    if i>=skip:
        print(f"  {ins.address:08x}  {ins.bytes.hex(' '):<22} {ins.mnemonic} {ins.op_str}")
        if i-skip>=lim: break
    i+=1
