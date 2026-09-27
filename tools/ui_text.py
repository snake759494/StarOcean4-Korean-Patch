import sys,io,json,struct
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
from mcdlib import *
def dec_ui(raw):
    out=[]; j=0; n=len(raw)
    while j<n:
        b=raw[j]
        if b==0: break
        if b>=0x80:
            if j+1>=n: break
            v=b|(raw[j+1]<<8); j+=2
            if v==0x0f80: out.append(' ')
            elif 0x0f9d<=v<=0x0fb6: out.append(chr(v-0x0f5c))
            elif 0x0fb7<=v<=0x0fd0: out.append(chr(v-0x0f56))
            elif v==0x8080: out.append('\n')
            else: out.append('\uFFFD')
        else:
            out.append('\uFFFD'); j+=1
    return ''.join(out)
if __name__=='__main__':
    packs=json.load(open('packs.json'))
    res={}
    for pi,pk in enumerate(packs):
        for a,b,c,s,eo in pk['e']:
            if a==30 and b==0x0233 and s<400000:
                try:
                    d=read_entry(pk['off']+eo,s); m=parse_mcd(d)
                    base=m['sect'][3]; nm=m['cnt'][2]
                    msgs=[]
                    for i in range(nm):
                        mid,mo=struct.unpack_from('<II',d,m['sect'][2]+i*8)
                        nxt=struct.unpack_from('<II',d,m['sect'][2]+(i+1)*8)[1] if i+1<nm else (len(d)-base)
                        msgs.append(dec_ui(bytes(d[base+mo:base+nxt])))
                    res[pi]=msgs
                except Exception: pass
                break
    json.dump(res,open('ui_en.json','w',encoding='utf-8'),ensure_ascii=False)
    tot=sum(len(v) for v in res.values())
    print(f"decoded id=30 (type 0x0231) for {len(res)} packs, {tot} strings")
    import re
    for kw in ['curricul','attle','utorial','elect','ontrol']:
        hits=[(pi,i,s) for pi,v in res.items() for i,s in enumerate(v) if kw in s]
        print(f"\n'{kw}': {len(hits)} hits")
        for pi,i,s in hits[:6]: print(f"   pack#{pi} #{i}: {s[:95]!r}")
