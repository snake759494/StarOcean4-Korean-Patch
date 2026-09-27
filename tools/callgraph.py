import sys,io,json,struct,bisect
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
GAME=r"C:\Program Files (x86)\Steam\steamapps\common\STAR OCEAN - THE LAST HOPE - 4K & Full HD Remaster"
d=open(GAME+r"\StarOceanTheLastHope.exe",'rb').read()
secs=json.load(open('pe.json'))['secs']
def f2r(off):
    for n,va,vsz,ro,rsz in secs:
        if ro<=off<ro+rsz: return va+(off-ro)
def r2f(rva):
    for n,va,vsz,ro,rsz in secs:
        if va<=rva<va+max(vsz,rsz): return ro+(rva-va)
pd=[s for s in secs if s[0]=='.pdata'][0]
funcs=[]
for i in range(pd[3],pd[3]+pd[4],12):
    b,e,u=struct.unpack_from('<III',d,i)
    if b==0: break
    funcs.append((b,e))
starts=[f[0] for f in funcs]
def owner(rva):
    i=bisect.bisect_right(starts,rva)-1
    if i>=0 and funcs[i][0]<=rva<funcs[i][1]: return funcs[i][0]
RO,RSZ=0x400,0x90b000
# build full direct-call edge list once
edges={}
for off in range(RO,RO+RSZ-5):
    if d[off]!=0xe8: continue
    rel=struct.unpack_from('<i',d,off+1)[0]
    src=f2r(off)
    if src is None: continue
    tgt=src+5+rel
    if not (0x1000<=tgt<0x90c000): continue
    o=owner(src)
    if o is None: continue
    edges.setdefault(tgt,set()).add((o,src))
json.dump({hex(k):[[hex(a),hex(b)] for a,b in v] for k,v in edges.items()}, open('calledges.json','w'))
print("edge targets:",len(edges))
def callers(t,depth=0,seen=None,maxd=3):
    seen=seen or set()
    if t in seen or depth>maxd: return
    seen.add(t)
    cs=edges.get(t,set())
    print("  "*depth+f"0x{t:x}  <- {len(cs)} caller(s)")
    for o,src in sorted(cs)[:6]:
        print("  "*(depth+1)+f"from func 0x{o:x} (call at 0x{src:x})")
        if len(cs)<=4: callers(o,depth+2,seen,maxd)
for t in (0x7a6a40,):
    callers(t)
