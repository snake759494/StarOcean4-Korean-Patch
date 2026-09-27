import sys,io,os,time
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8',errors='replace')
G=r"C:\Program Files (x86)\Steam\steamapps\common\STAR OCEAN - THE LAST HOPE - 4K & Full HD Remaster"
def scan(path):
    sz=os.path.getsize(path); f=open(path,'rb')
    CH=1<<26; pos=0; hits=[]; t=time.time()
    while pos<sz:
        f.seek(pos); buf=f.read(CH+1024)
        if not buf: break
        i=0
        while True:
            i=buf.find(b'glyf',i)
            if i<0 or i>=CH: break
            w=buf[max(0,i-2048):i+2048]
            if b'cmap' in w and b'head' in w and b'hhea' in w:
                hits.append(pos+i)
            i+=4
        pos+=CH
    return hits,time.time()-t,sz
for name in ("0000.bin","0001.bin"):
    p=os.path.join(G,name)
    h,el,sz=scan(p)
    print(f"{name}: {sz/2**30:.1f} GiB scanned in {el:.0f}s -> sfnt-like hits: {len(h)} {[hex(x) for x in h[:8]]}")
