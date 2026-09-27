import sys,io,json,struct,os,hashlib,time
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
import numpy as np
from PIL import Image,ImageDraw,ImageFont
os.chdir(r"C:\Users\Jay\so4_kr_patch_backup\tools"); sys.path.insert(0,os.getcwd())
from mcdlib import parse_mcd
from mcdlib0 import read_entry0
from slz import slz_decompress
from slzenc import slz_compress_v3
from bc7enc import encode_bc7_alpha
G=r"C:\Program Files (x86)\Steam\steamapps\common\STAR OCEAN - THE LAST HOPE - 4K & Full HD Remaster\0000.bin"
BAK=r"C:\Users\Jay\so4_kr_patch_backup"
FONT=r"C:\Windows\Fonts\malgun.ttf"; SYL="한글패치"
packs=json.load(open('packs0.json')); pk=packs[12]
a,b,c,usize,eo=[e for e in pk['e'] if e[0]==30 and e[1]==0x0261][0]
abs_off=pk['off']+eo
offs=sorted(e[4] for e in pk['e']); nxt=next((o for o in offs if o>eo),pk['tot']); span=nxt-eo
f=open(G,'rb'); f.seek(abs_off); tmpl=f.read(0x20); f.seek(abs_off); orig=f.read(span); f.close()
d=bytearray(read_entry0(abs_off,usize)); m=parse_mcd(d); o=m['sect']
ng=(o[5]-o[4])//24
p=o[6]+0x10; imgs=[]; fma=None
while p+16<=len(d):
    tag=bytes(d[p:p+4]); sz=struct.unpack_from('<I',d,p+4)[0]
    if sz==0 or p+sz>len(d): break
    if tag==b'Xgmi':
        w,h=struct.unpack_from('<HH',d,p+0x28); ds=struct.unpack_from('<I',d,p+0x3c)[0]; imgs.append((w,h,ds))
    if tag==b' FMA': fma=p+0x1d0
    p+=sz
W,H,_=imgs[0]
print(f"target pack#12 id=30 ty=0x0261 abs=0x{abs_off:x} usize=0x{usize:x} span=0x{span:x}")
print(f"  glyphs={ng} images={imgs}")
canvas=Image.new('L',(W,H),0); cache={}; used=0
for gi in range(ng):
    u0,v0,u1,v1=struct.unpack_from('<4f',d,o[4]+gi*24+8)
    x0,y0=int(round(u0*W)),int(round(v0*H)); x1,y1=int(round(u1*W)),int(round(v1*H))
    w,h=x1-x0,y1-y0
    if w<=0 or h<=0 or x1>W or y1>H: continue
    ch=SYL[gi%len(SYL)]; key=(ch,w,h)
    if key not in cache:
        t=Image.new('L',(w,h),0); td=ImageDraw.Draw(t)
        ft=ImageFont.truetype(FONT,max(8,int(h*0.82)))
        bb=td.textbbox((0,0),ch,font=ft)
        td.text(((w-(bb[2]-bb[0]))//2-bb[0],(h-(bb[3]-bb[1]))//2-bb[1]),ch,font=ft,fill=255)
        cache[key]=t
    canvas.paste(cache[key],(x0,y0)); used+=1
pos=fma
for (iw,ih,ids) in imgs:
    src=canvas if (iw,ih)==(W,H) else canvas.resize((iw,ih),Image.LANCZOS)
    blob=encode_bc7_alpha(np.asarray(src,dtype=np.uint8))
    assert len(blob)==ids
    d[pos:pos+ids]=blob; pos+=ids
new=slz_compress_v3(bytes(d),template=tmpl)
assert slz_decompress(new)[0]==bytes(d), "roundtrip failed"
hdrdiff=[hex(i) for i in range(0x20) if tmpl[i]!=new[i]]
print(f"  painted={used}/{ng}  comp={len(new)} span={span} fits={len(new)<=span}  hdr-diff={hdrdiff}")
assert len(new)<=span
bakf=os.path.join(BAK,f"z0_{abs_off:012x}_{span}.bin")
if not os.path.exists(bakf): open(bakf,'wb').write(orig)
with open(G,'r+b') as fh: fh.seek(abs_off); fh.write(new)
json.dump([{'game_bin':G,'offset':abs_off,'span':span,'orig_md5':hashlib.md5(orig).hexdigest(),
            'backup':bakf,'desc':'0000.bin pack#12 id=30 ty=0x0261 title/difficulty screen font'}],
          open(os.path.join(BAK,'patch_manifest_0000.json'),'w'),indent=1)
canvas.crop((0,0,700,140)).save('out_one.png') if os.path.isdir('.') else None
print("  PATCHED + backup saved")
