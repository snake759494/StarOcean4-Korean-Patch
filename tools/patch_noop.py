"""Control experiment: re-compress the SAME bytes, change no pixels.
If the game still crashes -> my SLZ output is non-conformant.
If the game runs fine    -> the crash comes from altering pixel data (checksum)."""
import sys,io,json,struct,os,hashlib
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
os.chdir(r"C:\Users\Jay\so4_kr_patch_backup\tools"); sys.path.insert(0,os.getcwd())
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
d=read_entry0(abs_off,usize)                       # decompress
new=slz_compress_v3(bytes(d),template=tmpl)        # recompress, identical payload
assert slz_decompress(new)[0]==bytes(d)
print(f"entry abs=0x{abs_off:x} usize=0x{usize:x} span=0x{span:x}")
print(f"  original compressed size = 0x{struct.unpack_from('<I',tmpl,8)[0]:x}")
print(f"  my       compressed size = 0x{len(new)-0x20:x}  total={len(new)} fits={len(new)<=span}")
print(f"  header diff vs original  = {[hex(i) for i in range(0x20) if tmpl[i]!=new[i]]}")
print(f"  payload identical to orig bytes? {new[:span]==orig}")
assert len(new)<=span
bakf=os.path.join(BAK,f"z0_{abs_off:012x}_{span}.bin")
if not os.path.exists(bakf): open(bakf,'wb').write(orig)
with open(G,'r+b') as fh: fh.seek(abs_off); fh.write(new)
json.dump([{'game_bin':G,'offset':abs_off,'span':span,'orig_md5':hashlib.md5(orig).hexdigest(),
            'backup':bakf,'desc':'CONTROL: recompress-only, pixels unchanged'}],
          open(os.path.join(BAK,'patch_manifest_0000.json'),'w'),indent=1)
print("  PATCHED (no pixel changes)")
