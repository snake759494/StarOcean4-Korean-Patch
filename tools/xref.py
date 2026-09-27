import numpy as np,sys
G=r"C:\Program Files (x86)\Steam\steamapps\common\STAR OCEAN - THE LAST HOPE - 4K & Full HD Remaster"
exe=open(G+r"\StarOceanTheLastHope.exe",'rb').read()
va,ro,rs=4096,1024,9482240
code=np.frombuffer(exe[ro:ro+rs],dtype=np.uint8)
n=len(code)-4
d=(code[:n].astype(np.int64)|(code[1:n+1].astype(np.int64)<<8)|(code[2:n+2].astype(np.int64)<<16)|(code[3:n+3].astype(np.int64)<<24))
d=np.where(d>=2**31,d-2**32,d)
pos=np.arange(n)+va
for a in sys.argv[1:]:
    t=int(a,16)
    for extra in (0,1,4):
        print(a,extra,[hex(x) for x in pos[(d+pos+4+extra)==t]][:40])
