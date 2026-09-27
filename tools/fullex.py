import sys,io,json,time
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
from mcdlib import *
from charmap import P38_EN
from fuzzy import Matcher,pack_glyphs
from textcodec import decode_tokens,tokens_to_str
packs=json.load(open('packs.json'))
def getm(pi,ty):
    pk=packs[pi]
    for a,b,c,s,eo in pk['e']:
        if a==58 and b==ty: return parse_mcd(read_entry(pk['off']+eo,s))
m38=getm(38,0x0233); g38,_=pack_glyphs(m38)
M=Matcher()
for i,ch in enumerate(P38_EN): M.add(g38[i],ch)
M.finalize()
out={}; t0=time.time()
for pi,pk in enumerate(packs):
    if not any(a==58 and b==0x0233 for a,b,c,s,eo in pk['e']): continue
    m=getm(pi,0x0233); gl,_=pack_glyphs(m)
    g2c=[]
    for im in gl:
        ch,d=M.match(im); g2c.append(ch if ch else '\uFFFD')
    out[pi]=[[m['msgs'][i][0], tokens_to_str(decode_tokens(msg_bytes(m,i),g2c))] for i in range(len(m['msgs']))]
json.dump(out,open('all_en_full.json','w',encoding='utf-8'),ensure_ascii=False)
print(f"extracted {len(out)} packs, {sum(len(v) for v in out.values())} messages in {time.time()-t0:.0f}s")
