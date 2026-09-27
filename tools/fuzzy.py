import json,numpy as np,hashlib
from mcdlib import *
from render import aif_alpha
BOX=(52,48)
def canon(im):
    a=np.zeros(BOX[::-1],dtype=np.float32)
    w=min(im.width,BOX[0]); h=min(im.height,BOX[1])
    a[:h,:w]=np.asarray(im,dtype=np.float32)[:h,:w]
    return a/255.0
def pack_glyphs(m):
    atlas,W,H,_,_=aif_alpha(m['data'],m['imgoff'])
    AW,AH=atlas.size; out=[]
    for adv,f1,u0,v0,u1,v1 in m['glyphs']:
        x0,y0=int(round(u0*AW)),int(round(v0*AH)); x1,y1=int(round(u1*AW)),int(round(v1*AH))
        out.append(atlas.crop((x0,y0,max(x1,x0+1),max(y1,y0+1))))
    return out,atlas
class Matcher:
    def __init__(self):
        self.vecs=[]; self.chars=[]
    def add(self,im,ch):
        self.vecs.append(canon(im).ravel()); self.chars.append(ch)
    def finalize(self):
        self.M=np.stack(self.vecs) if self.vecs else np.zeros((0,BOX[0]*BOX[1]),np.float32)
    def match(self,im,thr=6.0):
        v=canon(im).ravel()
        if len(self.M)==0: return None,1e9
        d=np.sqrt(((self.M-v)**2).sum(axis=1))
        i=int(d.argmin())
        return (self.chars[i], float(d[i])) if d[i]<thr else (None,float(d[i]))
