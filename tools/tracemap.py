import sys,io,os,json,re,bisect,collections
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
os.chdir(r"C:\Users\Jay\so4_kr_patch_backup\tools")
CSV=r"C:\Users\Jay\so4dump.csv"
# 1) FileObject -> archive name
obj2name={}
pat=re.compile(r'(0xFFFF[0-9A-Fa-f]{12,16})')
with open(CSV,encoding='utf-8',errors='replace') as f:
    for ln in f:
        low=ln.lower()
        if '0000.bin' in low or '0001.bin' in low:
            name='0000' if '0000.bin' in low else '0001'
            for p in pat.findall(ln):
                obj2name[p.upper()]=name
print("FileObject candidates for archives:",{k:v for k,v in obj2name.items()})
# 2) Read events joined by FileObject
reads=collections.defaultdict(list)
nread=0
with open(CSV,encoding='utf-8',errors='replace') as f:
    for ln in f:
        if not ln.startswith('      FileIo,'): continue
        fs=[x.strip() for x in ln.split(',')]
        if len(fs)<24 or fs[1]!='Read': continue
        nread+=1
        fo=fs[22].upper()
        if fo not in obj2name: continue
        try:
            off=int(fs[19]); size=int(fs[23])
        except ValueError: continue
        reads[obj2name[fo]].append((off,size))
print(f"\ntotal FileIo Read events: {nread}")
for k,v in reads.items():
    tot=sum(s for _,s in v)
    print(f"  {k}.bin: {len(v)} reads, {tot:,} bytes, offset range 0x{min(o for o,_ in v):x}..0x{max(o for o,_ in v):x}")
json.dump({k:v for k,v in reads.items()},open('reads.json','w'))
# 3) map to pack entries
def load(idx):
    packs=json.load(open(idx)); tab=[]
    for pi,pk in enumerate(packs):
        offs=sorted(e[4] for e in pk['e'])
        for a,b,c,s,eo in pk['e']:
            nxt=next((o for o in offs if o>eo),pk['tot'])
            tab.append((pk['off']+eo,pk['off']+nxt,pi,a,b,s))
    tab.sort(); return tab,[t[0] for t in tab]
T={'0001':load('packs.json'),'0000':load('packs0.json')}
hit=collections.Counter(); unmapped=collections.Counter()
for which,lst in reads.items():
    tab,starts=T[which]
    for off,size in lst:
        i=bisect.bisect_right(starts,off)-1
        if i>=0 and tab[i][0]<=off<tab[i][1]:
            e=tab[i]; hit[(which,e[2],e[3],e[4])]+=size
        else: unmapped[(which,off>>28)]+=size
print(f"\nentries actually read: {len(hit)}")
print(f"{'file':<6}{'pack':>7} {'id':>4} {'type':>8}   bytes")
for (w,pi,a,b),n in hit.most_common(45):
    print(f"{w:<6}{pi:>7} {a:>4}  0x{b:04x}  {n:,}")
if unmapped: print("\nunmapped:",[(k[0],hex(k[1]<<28),v) for k,v in unmapped.most_common(6)])
json.dump({f"{w}|{pi}|{a}|{b}":n for (w,pi,a,b),n in hit.items()},open('trace_hits.json','w'),indent=1)
