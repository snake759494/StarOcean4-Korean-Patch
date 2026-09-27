import os,struct,json,time
GAME=r"C:\Program Files (x86)\Steam\steamapps\common\STAR OCEAN - THE LAST HOPE - 4K & Full HD Remaster"
p=os.path.join(GAME,"0001.bin"); sz=os.path.getsize(p)
f=open(p,'rb')
packs=[]; off=0; t=time.time()
while off<sz:
    f.seek(off); h=f.read(16)
    if len(h)<16 or h[:4]!=b'KCAP':
        # try to resync forward at 0x800 alignment
        break
    ver,cnt,tot=struct.unpack_from('<III',h,4)
    ents=f.read(cnt*16)
    el=[]
    for j in range(cnt):
        a,b,c,s,eo=struct.unpack_from('<HHIII',ents,j*16)
        el.append((a,b,c,s,eo))
    packs.append({'off':off,'cnt':cnt,'tot':tot,'e':el})
    nxt=off+tot
    nxt=(nxt+0x7ff)&~0x7ff
    if nxt<=off: break
    off=nxt
print(f"packs={len(packs)} scanned to 0x{off:x} of 0x{sz:x} ({off/sz*100:.1f}%) in {time.time()-t:.1f}s")
json.dump(packs,open('packs.json','w'))
import collections
ids=collections.Counter(); types=collections.Counter()
for pk in packs:
    for a,b,c,s,eo in pk['e']:
        ids[a]+=1; types[b]+=1
print("entry ids:",dict(sorted(ids.items())))
print("entry types:",dict(sorted(types.items())))
print("total entries:",sum(pk['cnt'] for pk in packs))
