import sys,io,json,struct,time,os
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from mcdlib import *
from slz import slz_decompress
from slzenc import slz_compress_v3
from bc7enc import encode_bc7_alpha
GAMEBIN=r"C:\Program Files (x86)\Steam\steamapps\common\STAR OCEAN - THE LAST HOPE - 4K & Full HD Remaster\0001.bin"
FONT=r"C:\Windows\Fonts\malgun.ttf"
SYL="한글패치"
def locate():
    packs=json.load(open('packs.json')); pk=packs[668]
    offs=sorted(e[4] for e in pk['e'])
    for a,b,c,s,eo in pk['e']:
        if a==30 and b==0x0221 and s==0x510330:
            nxt=next((o for o in offs if o>eo), pk['tot'])
            return pk['off']+eo, nxt-eo, s
def build():
    abs_off,span,usize=locate()
    d=bytearray(read_entry(abs_off,usize))
    m=parse_mcd(d); o=m['sect']
    ng=(o[5]-o[4])//24
    base=o[6]; p=base+0x10; imgs=[]; fma=None
    while p+16<=len(d):
        tag=bytes(d[p:p+4]); sz=struct.unpack_from('<I',d,p+4)[0]
        if sz==0 or p+sz>len(d): break
        if tag==b'Xgmi':
            w,h=struct.unpack_from('<HH',d,p+0x28); ds=struct.unpack_from('<I',d,p+0x3c)[0]
            imgs.append((w,h,ds))
        if tag==b' FMA': fma=p+0x1d0
        p+=sz
    W,H,DS0=imgs[0]
    canvas=Image.new('L',(W,H),0); dr=ImageDraw.Draw(canvas)
    cache={}
    used=0
    for gi in range(ng):
        adv,f1=struct.unpack_from('<II',d,o[4]+gi*24)
        u0,v0,u1,v1=struct.unpack_from('<4f',d,o[4]+gi*24+8)
        x0,y0=int(round(u0*W)),int(round(v0*H)); x1,y1=int(round(u1*W)),int(round(v1*H))
        w,h=x1-x0,y1-y0
        if w<=0 or h<=0 or x1>W or y1>H: continue
        ch=SYL[gi%len(SYL)]
        key=(ch,w,h)
        if key not in cache:
            tile=Image.new('L',(w,h),0)
            fs=max(8,int(h*0.82))
            f=ImageFont.truetype(FONT,fs)
            td=ImageDraw.Draw(tile)
            bb=td.textbbox((0,0),ch,font=f)
            td.text(((w-(bb[2]-bb[0]))//2-bb[0], (h-(bb[3]-bb[1]))//2-bb[1]), ch, font=f, fill=255)
            cache[key]=tile
        canvas.paste(cache[key],(x0,y0)); used+=1
    print(f"  repainted {used}/{ng} glyph cells, distinct tiles={len(cache)}")
    a0=np.asarray(canvas,dtype=np.uint8)
    mipW,mipH,DS1=imgs[1]
    a1=np.asarray(canvas.resize((mipW,mipH),Image.LANCZOS),dtype=np.uint8)
    t=time.time(); b0=encode_bc7_alpha(a0); b1=encode_bc7_alpha(a1)
    print(f"  BC7 encoded {len(b0)}+{len(b1)} bytes in {time.time()-t:.1f}s (expect {DS0}+{DS1})")
    assert len(b0)==DS0 and len(b1)==DS1
    d[fma:fma+DS0]=b0; d[fma+DS0:fma+DS0+DS1]=b1
    return abs_off,span,usize,bytes(d),canvas
if __name__=='__main__':
    abs_off,span,usize,newbuf,canvas=build()
    canvas.crop((0,0,900,220)).save('out/repaint_preview.png')
    t=time.time(); blob=slz_compress_v3(newbuf); el=time.time()-t
    chk=slz_decompress(blob)[0]
    print(f"  SLZ v3: {len(blob)} bytes in {el:.0f}s  roundtrip={'OK' if chk==newbuf else 'FAIL'}")
    print(f"  SPAN = {span}   fits = {len(blob)<=span}   slack = {span-len(blob)}")
    open('newentry.bin','wb').write(blob)
    json.dump({'abs_off':abs_off,'span':span,'usize':usize},open('patchinfo.json','w'))
