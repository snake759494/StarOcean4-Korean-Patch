import os,struct,json,io,collections
from mcdlib import *
from PIL import Image
def dds_bc7(data,w,h):
    return (struct.pack('<4sI',b'DDS ',124)+struct.pack('<IIIIII',0x1|0x2|0x4|0x1000|0x80000,h,w,len(data),0,0)
            +b'\0'*44+struct.pack('<II4sIIIII',32,0x4,b'DX10',0,0,0,0,0)
            +struct.pack('<IIIII',0x1000,0,0,0,0)+struct.pack('<IIIII',98,3,0,1,0)+data)
def aif_alpha(d,base):
    """base = offset of ' FIA' block inside d"""
    o=base+0x10; imgs=[]; fma=None
    while o+16<=len(d):
        tag=bytes(d[o:o+4]); sz=struct.unpack_from('<I',d,o+4)[0]
        if sz==0 or o+sz>len(d): break
        if tag==b'Xgmi':
            w,h=struct.unpack_from('<HH',d,o+0x28); ds=struct.unpack_from('<I',d,o+0x3c)[0]; imgs.append((w,h,ds))
        if tag==b' FMA': fma=o+0x1d0
        o+=sz
    w,h,ds=imgs[0]
    im=Image.open(io.BytesIO(dds_bc7(bytes(d[fma:fma+ds]),w,h))); im.load()
    return im.convert('RGBA').getchannel('A'),w,h,imgs,fma
def render_msg(atlas,W,H,glyphs,raw,maxw=1900,lh=44):
    """decode index stream and blit"""
    W_,H_=atlas.size
    lines=[[]]; i=0
    while i<len(raw):
        b=raw[i]
        if b==0: break
        if b>=0x80:
            nb=raw[i+1] if i+1<len(raw) else 0
            if b==0x80 and nb==0x80: lines.append([]); i+=2; continue
            i+=2; continue                      # other control: skip
        gi=b-1
        if 0<=gi<len(glyphs): lines[-1].append(glyphs[gi])
        i+=1
    imgs=[]
    for ln in lines:
        wsum=sum(g[0] for g in ln) or 1
        canv=Image.new('L',(max(wsum,1),lh),0); x=0
        for adv,f1,u0,v0,u1,v1 in ln:
            x0,y0=int(round(u0*W_)),int(round(v0*H_)); x1,y1=int(round(u1*W_)),int(round(v1*H_))
            if x1>x0 and y1>y0:
                canv.paste(atlas.crop((x0,y0,x1,y1)),(x,2))
            x+=adv
        imgs.append(canv)
    return imgs
