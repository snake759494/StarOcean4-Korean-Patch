import sys,io,json,struct,time,os,hashlib
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from mcdlib import *
from slz import slz_decompress
from slzenc import slz_compress_v3
from bc7enc import encode_bc7_alpha
GAMEBIN=r"C:\Program Files (x86)\Steam\steamapps\common\STAR OCEAN - THE LAST HOPE - 4K & Full HD Remaster\0001.bin"
BAKDIR=r"C:\Users\Jay\so4_kr_patch_backup"
FONT=r"C:\Windows\Fonts\malgun.ttf"
SYL="한글패치"
os.makedirs(BAKDIR,exist_ok=True)
packs=json.load(open('packs.json'))
pk=packs[668]; offs=sorted(e[4] for e in pk['e'])
targets=[]
for a,b,c,s,eo in pk['e']:
    if a==30 and s>200000:
        nxt=next((o for o in offs if o>eo), pk['tot'])
        targets.append((b,pk['off']+eo,nxt-eo,s,eo))
print(f"{len(targets)} font entries\n")
manifest=[]
for ty,abs_off,span,usize,eo in targets:
    t0=time.time()
    d=bytearray(read_entry(abs_off,usize)); m=parse_mcd(d); o=m['sect']
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
    canvas=Image.new('L',(W,H),0); cache={}; used=0
    for gi in range(ng):
        u0,v0,u1,v1=struct.unpack_from('<4f',d,o[4]+gi*24+8)
        x0,y0=int(round(u0*W)),int(round(v0*H)); x1,y1=int(round(u1*W)),int(round(v1*H))
        w,h=x1-x0,y1-y0
        if w<=0 or h<=0 or x1>W or y1>H: continue
        ch=SYL[gi%len(SYL)]; key=(ch,w,h)
        if key not in cache:
            tile=Image.new('L',(w,h),0); td=ImageDraw.Draw(tile)
            f=ImageFont.truetype(FONT,max(8,int(h*0.82)))
            bb=td.textbbox((0,0),ch,font=f)
            td.text(((w-(bb[2]-bb[0]))//2-bb[0],(h-(bb[3]-bb[1]))//2-bb[1]),ch,font=f,fill=255)
            cache[key]=tile
        canvas.paste(cache[key],(x0,y0)); used+=1
    pos=fma
    for (iw,ih,ids) in imgs:
        src=canvas if (iw,ih)==(W,H) else canvas.resize((iw,ih),Image.LANCZOS)
        blob=encode_bc7_alpha(np.asarray(src,dtype=np.uint8))
        assert len(blob)==ids,(len(blob),ids)
        d[pos:pos+ids]=blob; pos+=ids
    newblob=slz_compress_v3(bytes(d))
    ok=slz_decompress(newblob)[0]==bytes(d)
    fits=len(newblob)<=span
    print(f"type=0x{ty:04x} glyphs={ng:<4} tex={W}x{H} repainted={used:<4} "
          f"comp={len(newblob)} span={span} fits={fits} rt={ok} ({time.time()-t0:.0f}s)")
    if not (ok and fits):
        print("   -> SKIPPED"); continue
    bak=os.path.join(BAKDIR,f"orig_{abs_off:012x}_{span}.bin")
    with open(GAMEBIN,'rb') as f:
        f.seek(abs_off); orig=f.read(span)
    if not os.path.exists(bak): open(bak,'wb').write(orig)
    with open(GAMEBIN,'r+b') as f:
        f.seek(abs_off); f.write(newblob)
    manifest.append({'game_bin':GAMEBIN,'offset':abs_off,'span':span,
                     'orig_md5':hashlib.md5(orig).hexdigest(),'backup':bak,
                     'desc':f'pack#668 id=30 type=0x{ty:04x} font atlas'})
    print("   -> PATCHED")
json.dump(manifest,open(os.path.join(BAKDIR,'patch_manifest_all.json'),'w'),indent=1)
print(f"\n{len(manifest)} entries patched; manifest at {BAKDIR}")
