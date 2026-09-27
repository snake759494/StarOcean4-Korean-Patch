import sys,io,json
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
from mcdlib import *
from charmap import P38_EN
from fuzzy import Matcher,pack_glyphs
from textcodec import decode_tokens,tokens_to_str
packs=json.load(open('packs.json'))
def getm(pi,ty=0x0233):
    pk=packs[pi]
    for a,b,c,s,eo in pk['e']:
        if a==58 and b==ty: return parse_mcd(read_entry(pk['off']+eo,s))
m38=getm(38); g38,_=pack_glyphs(m38)
M=Matcher()
for i,ch in enumerate(P38_EN): M.add(g38[i],ch)
M.finalize()
out=[]
for pi,pk in enumerate(packs):
    if not any(a==58 and b==0x0233 for a,b,c,s,eo in pk['e']): continue
    m=getm(pi); gl,_=pack_glyphs(m)
    g2c=[]
    for im in gl:
        ch,d=M.match(im); g2c.append(ch if ch else '\uFFFD')
    msgs=[tokens_to_str(decode_tokens(msg_bytes(m,i),g2c)) for i in range(min(3,len(m['msgs'])))]
    out.append({'pack':pi,'n':len(m['msgs']),'first':msgs})
json.dump(out,open('pack_ident.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)
print(f"{len(out)} story packs, {sum(o['n'] for o in out)} messages total\n")
for o in out:
    s=' / '.join(x.replace('\n',' ') for x in o['first'])[:100]
    print(f"p{o['pack']:<5} n={o['n']:<4} {s}")
