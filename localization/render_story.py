"""Render a Japanese story resource from its own original glyph atlas."""
from pathlib import Path
import sys,json,struct,io
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,str(ROOT))
from verify_slz import decode_native_slz
from mcdlib import parse_mcd
from render import aif_alpha,dds_bc7
from localization.codec import messages
from PIL import Image,ImageDraw
key=sys.argv[1];archive,pi,ei=key.split('_');pi=int(pi);ei=int(ei)
packs=json.loads((ROOT/'tools'/('packs0.json' if archive=='0000' else 'packs.json')).read_text())
p=packs[pi];e=p['e'][ei];span=min([r[4] for r in p['e'] if r[4]>e[4]]+[p['tot']])-e[4]
original=ROOT/'build'/f'p{pi}_e{ei}.original.bin'
if archive=='0000' and original.exists():raw=original.read_bytes()
else:
    game=Path(r'C:\Program Files (x86)\Steam\steamapps\common\STAR OCEAN - THE LAST HOPE - 4K & Full HD Remaster')
    with (game/(archive+'.bin')).open('rb') as f:f.seek(p['off']+e[4]);raw=f.read(span)
d=decode_native_slz(raw)[0];m=parse_mcd(d)
_,w,h,imgs,pos=aif_alpha(d,m['imgoff'])
atlas=Image.open(io.BytesIO(dds_bc7(d[pos:pos+imgs[0][2]],w,h))).convert('RGBA')
count=sum(struct.unpack_from('<I',d,m['sect'][0]+16*i)[0] for i in range(m['cnt'][0]))
glyphs=[struct.unpack_from('<II4f',d,m['sect'][4]+i*24) for i in range(count)]
rows=list(messages(d).items());perpage=12
for page in range((len(rows)+perpage-1)//perpage):
    out=Image.new('RGB',(1500,1800),(20,25,35));draw=ImageDraw.Draw(out)
    for line,(identifier,text) in enumerate(rows[page*perpage:(page+1)*perpage]):
        x=70;y=line*150;draw.text((2,y+5),str(identifier),fill='white');i=0
        while i<len(text) and text[i]:
            n=text[i];i+=1
            if n>=128:n=(n&127)|(text[i]<<7);i+=1
            if n>=0x4000:
                command=text[i-2]
                if command in (0x80,0x81):x=70;y+=34
                elif command==0x93:
                    name=struct.unpack_from('<H',text,i)[0];i=text.index(0,i+2)+1
                    label=f'[NAME:{name}]';draw.text((x,y+12),label,fill='yellow');x+=len(label)*7
                elif command==0xa8:i+=4
                elif command in (0x84,0xac):i+=1
                elif command==0x94:i+=2
                elif command in (0x90,0x91):pass
                elif command not in (0x82,0x85):raise ValueError((identifier,hex(command)))
                continue
            a,_,u,v,r,b=glyphs[n-1]
            tile=atlas.crop((round(u*w),round(v*h),round(r*w),round(b*h)))
            tile=tile.resize((max(1,round(tile.width*.8)),max(1,round(tile.height*.8))),Image.Resampling.LANCZOS)
            if x+tile.width>1490:x=70;y+=34
            out.paste(tile,(x,y),tile);x+=round(a*.8)
    out.save(ROOT/'localization'/f'story_{key}_{page+1}.png')
print('Rendered',len(rows),'story messages',key)
