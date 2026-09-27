import sys,io,json,struct,os
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
os.chdir(r"C:\Users\Jay\so4_kr_patch_backup\tools"); sys.path.insert(0,os.getcwd())
from mcdlib import parse_mcd
from mcdlib0 import read_entry0
def dec(raw):
    out=[]; j=0; n=len(raw)
    while j<n:
        b=raw[j]
        if b==0: break
        if b>=0x80:
            if j+1>=n: break
            v=b|(raw[j+1]<<8); j+=2
            if v==0x8080: out.append('\n')
            elif v==0x0f80: out.append(' ')
            elif 0x0f9d<=v<=0x0fb6: out.append(chr(v-0x0f5c))
            elif 0x0fb7<=v<=0x0fd0: out.append(chr(v-0x0f56))
            else: out.append('\uFFFD')
        else: out.append('\uFFFD'); j+=1
    return ''.join(out)
packs=json.load(open('packs0.json'))
res={}
for pi,pk in enumerate(packs):
    for a,b,c,s,eo in pk['e']:
        if a!=30 or b!=0x0233: continue
        try:
            d=read_entry0(pk['off']+eo,s)
            if bytes(d[:4])!=b'pDCM': continue
            m=parse_mcd(d); o=m['sect']; nm=m['cnt'][2]
            if not nm: continue
            base=o[3]; end=o[4] if o[4] else len(d)
            msgs=[]
            for i in range(nm):
                mid,mo=struct.unpack_from('<II',d,o[2]+i*8)
                nxt=struct.unpack_from('<II',d,o[2]+(i+1)*8)[1] if i+1<nm else (end-base)
                msgs.append(dec(bytes(d[base+mo:base+nxt])))
            res[pi]=msgs
        except Exception: pass
json.dump(res,open('ui0_en.json','w',encoding='utf-8'),ensure_ascii=False)
print(f"0000.bin id=30 EN entries decoded: {len(res)} packs, {sum(len(v) for v in res.values())} strings")
for kw in ['ifficult','tandard','ptimal','ecommend','hoose','annot be changed','uring the game']:
    hits=[(pi,i,s) for pi,v in res.items() for i,s in enumerate(v) if kw in s]
    print(f"\n'{kw}': {len(hits)}")
    for pi,i,s in hits[:6]: print(f"   pack#{pi} #{i}: {s[:95]!r}")
