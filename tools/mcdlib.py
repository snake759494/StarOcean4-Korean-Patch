import os,struct,json,io
from slz import slz_decompress
GAME=r"C:\Program Files (x86)\Steam\steamapps\common\STAR OCEAN - THE LAST HOPE - 4K & Full HD Remaster"
BIN=os.path.join(GAME,"0001.bin")
_f=open(BIN,'rb')
def read_entry(off,size):
    _f.seek(off); raw=_f.read(size+0x40)
    return slz_decompress(raw)[0] if raw[:3]==b'SLZ' else raw[:size]
def parse_mcd(d):
    assert bytes(d[0:4])==b'pDCM'
    o=[struct.unpack_from('<I',d,0x18+i*4)[0] for i in range(7)]
    c=[struct.unpack_from('<I',d,0x34+i*4)[0] for i in range(4)]
    hdr=struct.unpack_from('<4I',d,0x90)          # nglyph, ascent, cellw, cellh
    nmsg=c[2]
    msgs=[]
    for i in range(nmsg):
        mid,mo=struct.unpack_from('<II',d,o[2]+i*8)
        msgs.append((mid,mo))
    textbase=o[3]; textend=o[4]
    glyphs=[]
    ng=hdr[0]
    for i in range(ng):
        p=o[4]+i*24
        if p+24>len(d): break
        adv,f1=struct.unpack_from('<II',d,p)
        u0,v0,u1,v1=struct.unpack_from('<4f',d,p+8)
        glyphs.append((adv,f1,u0,v0,u1,v1))
    texw,texh=struct.unpack_from('<II',d,o[5])
    return dict(sect=o,cnt=c,hdr=hdr,msgs=msgs,textbase=textbase,textend=textend,
                glyphs=glyphs,texw=texw,texh=texh,imgoff=o[6],data=d)
def msg_bytes(m,i):
    d=m['data']; base=m['textbase']
    start=base+m['msgs'][i][1]
    end=base+m['msgs'][i+1][1] if i+1<len(m['msgs']) else m['textend']
    return bytes(d[start:end])
