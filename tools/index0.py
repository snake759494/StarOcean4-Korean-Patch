import sys,io,os,time,struct,json,collections
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
G=r"C:\Program Files (x86)\Steam\steamapps\common\STAR OCEAN - THE LAST HOPE - 4K & Full HD Remaster"
Z=os.path.join(G,"0000.bin")
sz=os.path.getsize(Z); f=open(Z,'rb')
CH=1<<26; pos=0; hits=[]; t=time.time()
while pos<sz:
    f.seek(pos); buf=f.read(CH+8)
    if not buf: break
    i=0
    while True:
        i=buf.find(b'KCAP',i)
        if i<0 or i>=CH: break
        if (pos+i)%0x800==0: hits.append(pos+i)
        i+=4
    pos+=CH
print(f"aligned KCAP: {len(hits)} ({time.time()-t:.0f}s)")
packs=[]
for h in hits:
    f.seek(h); hd=f.read(16)
    ver,cnt,tot=struct.unpack_from('<III',hd,4)
    if ver!=0x706 or not (0<cnt<4096) or tot<16: continue
    ents=f.read(cnt*16)
    if len(ents)<cnt*16: continue
    el=[]
    ok=True
    for j in range(cnt):
        a,b,c,s,eo=struct.unpack_from('<HHIII',ents,j*16)
        if eo>=tot or s>(1<<30): ok=False; break
        el.append((a,b,c,s,eo))
    if ok: packs.append({'off':h,'cnt':cnt,'tot':tot,'e':el})
print(f"valid packs: {len(packs)}  total entries: {sum(p['cnt'] for p in packs)}")
json.dump(packs,open('packs0.json','w'))
ids=collections.Counter(); tys=collections.Counter()
for p in packs:
    for a,b,c,s,eo in p['e']: ids[a]+=1; tys[b]+=1
print("ids:",dict(sorted(ids.items())))
print("types:",dict(sorted(tys.items())))
