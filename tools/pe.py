import os,struct,re
GAME=r"C:\Program Files (x86)\Steam\steamapps\common\STAR OCEAN - THE LAST HOPE - 4K & Full HD Remaster"
data=open(os.path.join(GAME,"StarOceanTheLastHope.exe"),'rb').read()
e_lfanew=struct.unpack_from('<I',data,0x3c)[0]
assert data[e_lfanew:e_lfanew+4]==b'PE\0\0'
nsec=struct.unpack_from('<H',data,e_lfanew+6)[0]
optsz=struct.unpack_from('<H',data,e_lfanew+20)[0]
magic=struct.unpack_from('<H',data,e_lfanew+24)[0]
imgbase=struct.unpack_from('<Q',data,e_lfanew+24+24)[0]
print("sections",nsec,"magic",hex(magic),"imagebase",hex(imgbase))
secs=[]
so=e_lfanew+24+optsz
for i in range(nsec):
    b=data[so+i*40:so+(i+1)*40]
    name=b[:8].rstrip(b'\0').decode()
    vsz,va,rsz,ro=struct.unpack_from('<IIII',b,8)
    secs.append((name,va,vsz,ro,rsz))
    print(f"  {name:<8} VA=0x{va:08x} VSz=0x{vsz:08x} Raw=0x{ro:08x} RSz=0x{rsz:08x}")
def f2r(off):
    for n,va,vsz,ro,rsz in secs:
        if ro<=off<ro+rsz: return va+(off-ro)
    return None
def r2f(rva):
    for n,va,vsz,ro,rsz in secs:
        if va<=rva<va+max(vsz,rsz): return ro+(rva-va)
    return None
import json
json.dump({'imgbase':imgbase,'secs':secs},open('pe.json','w'))
print("\nSLZ string file off 0x9142a8 -> RVA", hex(f2r(0x9142a8)))
# find 4-byte immediates 'SLZ\0'
hits=[m.start() for m in re.finditer(rb'\x53\x4c\x5a\x00',data)]
print("'SLZ\0' occurrences:", [hex(h) for h in hits])
for h in hits:
    print("   ", hex(h), "rva", hex(f2r(h)) if f2r(h) else None, "sec", next((n for n,va,vsz,ro,rsz in secs if ro<=h<ro+rsz),'?'))
