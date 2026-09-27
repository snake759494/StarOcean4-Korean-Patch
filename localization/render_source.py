"""Read-only Japanese source proof sheets from original decoded RGBA."""
import sys,json,struct,io
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
sys.path.insert(0,str(ROOT))
from verify_slz import decode_native_slz
from mcdlib import parse_mcd
from render import aif_alpha,dds_bc7
from localization.codec import messages
from localization.battle_records_ko import NUMBER,PATTERNS,K
from PIL import Image,ImageDraw

def load(name):
    data=decode_native_slz((ROOT/'build'/name).read_bytes())[0]
    m=parse_mcd(data); _,w,h,imgs,pos=aif_alpha(data,m['imgoff'])
    rgba=Image.open(io.BytesIO(dds_bc7(data[pos:pos+imgs[0][2]],w,h))).convert('RGBA')
    count=sum(struct.unpack_from('<I',data,m['sect'][0]+16*i)[0] for i in range(m['cnt'][0]))
    glyphs=[struct.unpack_from('<II4f',data,m['sect'][4]+24*i) for i in range(count)]
    return data,rgba,glyphs

data,local,localglyphs=load('p5_e0.original.bin')
_,globalatlas,globalglyphs=load('p0_e65.original.bin')
raws=messages(data)
english=json.loads((ROOT/'localization/source/0000_3_0.json').read_text(encoding='utf-8'))
selected=[];seen=set()
remaining='--remaining' in sys.argv
for row in english:
    if not 50000<=row['id']<51000:continue
    template=row['source'] if remaining else NUMBER.sub('{n}',row['source'].strip())
    if (row['id'] not in K if remaining else template in PATTERNS) and template not in seen:
        selected.append(row);seen.add(template)
skills='--skills' in sys.argv
if skills:selected=[row for row in english if 20000<=row['id']<21000]
range_mode='--range' in sys.argv
if range_mode:
    at=sys.argv.index('--range');lo,hi=map(int,sys.argv[at+1:at+3])
    selected=[row for row in english if lo<=row['id']<hi]
    if '--ids' in sys.argv:
        wanted=set(map(int,sys.argv[sys.argv.index('--ids')+1].split(',')))
        selected=[row for row in selected if row['id'] in wanted]
perpage=12 if range_mode else 24
rowheight=150 if range_mode else 66
if '--compact' in sys.argv:perpage=32;rowheight=50
for page in range((len(selected)+perpage-1)//perpage):
    out=Image.new('RGB',(1500,perpage*rowheight),(20,25,35));draw=ImageDraw.Draw(out)
    for rownum,row in enumerate(selected[page*perpage:page*perpage+perpage]):
        x=100;y=rownum*rowheight;draw.text((2,y+7),str(row['id']),fill='white');raw=raws[row['id']];i=0
        in_name=False
        while i<len(raw):
            if raw[i]==0:
                if in_name:in_name=False;i+=1;continue
                break
            n=raw[i];i+=1
            if n>=128:n=(n&127)|(raw[i]<<7);i+=1
            if n>=0x4000:
                command=raw[i-2]
                if command==0x93:i+=2;in_name=True
                elif command==0xa8:i+=4
                elif command in (0x84,0xac):i+=1
                elif command==0x94:i+=2
                elif command not in (0x80,0x81,0x82,0x85):break
                continue
            assert n<0x4000,(row['id'],hex(n))
            atlas,glyphs,index=(local,localglyphs,n-3073) if n>=3073 else (globalatlas,globalglyphs,n-1)
            advance,_,u,v,r,b=glyphs[index]
            tile=atlas.crop((round(u*atlas.width),round(v*atlas.height),round(r*atlas.width),round(b*atlas.height)))
            tile=tile.resize((max(1,round(tile.width*.4)),max(1,round(tile.height*.4))),Image.Resampling.LANCZOS)
            if range_mode and x+tile.width>1490:x=100;y+=32
            out.paste(tile,(x,y),tile);x+=round(advance*.4)
        draw.text((100,y+34),row['source'],fill=(170,180,190))
    prefix='skills' if skills else 'battle_remaining' if remaining else 'battle_source'
    if range_mode:prefix=f'proof_{lo}'
    out.save(ROOT/'localization'/f'{prefix}_{page+1}.png')
print('Rendered',len(selected),'distinct condition patterns')
