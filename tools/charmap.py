import json,hashlib
from mcdlib import *
from render import aif_alpha
from PIL import Image
P38_EN=("F i n a l y ! _SP_ G O D W e r o u g s t h v p c w ? - ' Y j k m T x b , d H E I . L S * A f U q Q \" C M R 0 3 P B "
        "\u2014 z N K ; 4 % 6").split()
P38_EN=[' ' if c=='_SP_' else c for c in P38_EN]
def glyph_bitmaps(m):
    atlas,W,H,_,_=aif_alpha(m['data'],m['imgoff'])
    AW,AH=atlas.size; out=[]
    for adv,f1,u0,v0,u1,v1 in m['glyphs']:
        x0,y0=int(round(u0*AW)),int(round(v0*AH)); x1,y1=int(round(u1*AW)),int(round(v1*AH))
        im=atlas.crop((x0,y0,max(x1,x0+1),max(y1,y0+1)))
        out.append((im, hashlib.md5(im.tobytes()+bytes([im.width,im.height])).hexdigest()))
    return out,atlas
def build_ref():
    packs=json.load(open('packs.json')); pk=packs[38]
    for a,b,c,s,eo in pk['e']:
        if a==58 and b==0x0233: m=parse_mcd(read_entry(pk['off']+eo,s)); break
    bms,_=glyph_bitmaps(m)
    ref={}
    for gi,(im,h) in enumerate(bms):
        if gi<len(P38_EN): ref[h]=P38_EN[gi]
    return ref
def decode_text(m, ref):
    bms,_=glyph_bitmaps(m)
    g2c=[ref.get(h,'\uFFFD') for im,h in bms]
    out=[]
    for i in range(len(m['msgs'])):
        r=msg_bytes(m,i); s=[]; j=0
        while j<len(r):
            b=r[j]
            if b==0: break
            if b>=0x80:
                nb=r[j+1] if j+1<len(r) else 0
                s.append('\n' if (b==0x80 and nb==0x80) else '{%02X%02X}'%(b,nb)); j+=2; continue
            gi=b-1
            s.append(g2c[gi] if 0<=gi<len(g2c) else '\uFFFD'); j+=1
        out.append((m['msgs'][i][0], ''.join(s)))
    return out,g2c
