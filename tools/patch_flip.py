"""Test A: change only a handful of pixel bytes, keep everything else identical.
crash -> a content checksum exists somewhere
ok    -> content changes are fine; the problem is my BC7 output"""
import sys,io,json,struct,os,hashlib
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
os.chdir(r"C:\Users\Jay\so4_kr_patch_backup\tools"); sys.path.insert(0,os.getcwd())
from mcdlib import parse_mcd
from mcdlib0 import read_entry0
from slz import slz_decompress
from slzenc import slz_compress_v3
G=r"C:\Program Files (x86)\Steam\steamapps\common\STAR OCEAN - THE LAST HOPE - 4K & Full HD Remaster\0000.bin"
BAK=r"C:\Users\Jay\so4_kr_patch_backup"
packs=json.load(open('packs0.json')); pk=packs[12]
a,b,c,usize,eo=[e for e in pk['e'] if e[0]==30 and e[1]==0x0261][0]
abs_off=pk['off']+eo
offs=sorted(e[4] for e in pk['e']); nxt=next((o for o in offs if o>eo),pk['tot']); span=nxt-eo
with open(G,'rb') as f:
    f.seek(abs_off); tmpl=f.read(0x20); f.seek(abs_off); orig=f.read(span)
d=bytearray(read_entry0(abs_off,usize)); m=parse_mcd(d); o=m['sect']
p=o[6]+0x10; imgs=[]; fma=None
while p+16<=len(d):
    tag=bytes(d[p:p+4]); sz=struct.unpack_from('<I',d,p+4)[0]
    if sz==0 or p+sz>len(d): break
    if tag==b'Xgmi':
        w,h=struct.unpack_from('<HH',d,p+0x28); ds=struct.unpack_from('<I',d,p+0x3c)[0]; imgs.append((w,h,ds))
    if tag==b' FMA': fma=p+0x1d0
    p+=sz
# flip the low-order alpha-index bytes of 32 consecutive blocks near the middle of image 0
start=fma+(imgs[0][2]//2 & ~15)
changed=0
for blk in range(32):
    q=start+blk*16
    d[q+15]^=0xFF          # touch only index bits, keeps mode byte intact
    changed+=1
print(f"entry abs=0x{abs_off:x} usize=0x{usize:x} span=0x{span:x}")
print(f"  pixel region 0x{fma:x}, img0 size 0x{imgs[0][2]:x}")
print(f"  modified {changed} blocks (1 byte each) at 0x{start:x}, mode bytes untouched")
new=slz_compress_v3(bytes(d),template=tmpl)
assert slz_decompress(new)[0]==bytes(d)
print(f"  comp={len(new)} span={span} fits={len(new)<=span} hdrdiff={[hex(i) for i in range(0x20) if tmpl[i]!=new[i]]}")
assert len(new)<=span
bakf=os.path.join(BAK,f"z0_{abs_off:012x}_{span}.bin")
if not os.path.exists(bakf): open(bakf,'wb').write(orig)
with open(G,'r+b') as fh: fh.seek(abs_off); fh.write(new)
json.dump([{'game_bin':G,'offset':abs_off,'span':span,'orig_md5':hashlib.md5(orig).hexdigest(),
            'backup':bakf,'desc':'TEST A: 32 pixel bytes flipped'}],
          open(os.path.join(BAK,'patch_manifest_0000.json'),'w'),indent=1)
print("  PATCHED")
