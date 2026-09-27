import sys,io,json,struct,os
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
os.chdir(r"C:\Users\Jay\so4_kr_patch_backup\tools"); sys.path.insert(0,os.getcwd())
from mcdlib import parse_mcd, read_entry
from mcdlib0 import read_entry0
def shape(raw):
    """line char-counts; handles 1-byte glyph idx and 2-byte charset codes"""
    lines=[0]; j=0; n=len(raw)
    while j<n:
        b=raw[j]
        if b==0: break
        if b>=0x80:
            if j+1>=n: break
            v=b|(raw[j+1]<<8); j+=2
            if v==0x8080: lines.append(0)
            else: lines[-1]+=1
        else:
            lines[-1]+=1; j+=1
    return lines
TARGETS=[[10,26],[10],[26],[2],[5]]
def scan(tag, packs, reader):
    found=[]
    for pi,pk in enumerate(packs):
        for a,b,c,s,eo in pk['e']:
            if a!=30: continue
            try:
                d=reader(pk['off']+eo,s)
                if bytes(d[:4])!=b'pDCM': continue
                m=parse_mcd(d); o=m['sect']; nm=m['cnt'][2]
                if not nm: continue
                base=o[3]; end=o[4] if o[4] else len(d)
                for i in range(nm):
                    mid,mo=struct.unpack_from('<II',d,o[2]+i*8)
                    nxt=struct.unpack_from('<II',d,o[2]+(i+1)*8)[1] if i+1<nm else (end-base)
                    sh=shape(bytes(d[base+mo:base+nxt]))
                    if sh==[10,26]:
                        found.append((tag,pi,a,b,s,i,mid,sh))
            except Exception: pass
    return found
res=[]
res+=scan('0001', json.load(open('packs.json')), read_entry)
res+=scan('0000', json.load(open('packs0.json')), read_entry0)
print(f"messages with line shape [10,26]: {len(res)}")
for t,pi,a,b,s,i,mid,sh in res[:25]:
    print(f"   {t} pack#{pi:<5} id={a} ty=0x{b:04x} usize=0x{s:<8x} msg#{i} id={mid}")
json.dump(res,open('screenhits.json','w'))
