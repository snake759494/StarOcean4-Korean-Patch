import struct
CHUNK=0x10000
def _compress_chunk(src, s, e):
    """LZSS v1: 8-bit flags LSB-first, 1=literal; match=2B dist(12b, relative)+len(4b)+3"""
    out=bytearray(); flags=0; nf=0; pend=bytearray()
    ht={}
    i=s
    while i<e:
        best_len=0; best_dist=0
        if i+3<=e:
            key=src[i:i+3]
            lo=max(s,i-4095)
            for cand in reversed(ht.get(bytes(key),())):
                if cand<lo: break
                l=0; maxl=min(18,e-i)
                while l<maxl and src[cand+l]==src[i+l]: l+=1
                if l>best_len:
                    best_len=l; best_dist=i-cand
                    if l==18: break
        if best_len>=3:
            tok=best_dist|((best_len-3)<<12)
            pend+=bytes((tok&0xff,(tok>>8)&0xff))
            n=best_len
        else:
            flags|=1<<nf
            pend.append(src[i]); n=1
        nf+=1
        if nf==8:
            out.append(flags); out+=pend; flags=0; nf=0; pend=bytearray()
        for k in range(n):
            j=i+k
            if j+3<=e: ht.setdefault(bytes(src[j:j+3]),[]).append(j)
        i+=n
    # The native decoder terminates on distance=0, NOT the output length.
    pend += b'\x00\x00'
    out.append(flags); out += pend
    return bytes(out)
def slz_compress(data, ver=1, hdr_template=None):
    n=len(data); body=bytearray()
    off=0
    while off<n:
        cu=min(CHUNK,n-off)
        c=_compress_chunk(data,off,off+cu)
        if len(c)>=cu:                      # stored
            body+=struct.pack('<H',cu & 0xffff)+data[off:off+cu]
        else:
            body+=struct.pack('<H',len(c))+c
        off+=cu
    h=bytearray(32)
    h[0:4]=b'SLZ'+bytes([ver])
    h[4]=0; h[5]=1; struct.pack_into('<H',h,6,0x25)
    struct.pack_into('<I',h,8,len(body))
    struct.pack_into('<I',h,12,n)
    struct.pack_into('<I',h,0x14,0x20)
    h[0x19]=CHUNK>>10
    return bytes(h)+bytes(body)

def _compress_chunk_v3(src, s, e):
    """SLZ v3: 16-bit words. flag word (16 ops, LSB first, 1=literal word).
       match word: dist words (12b, relative, !=0) | (len_words-2)<<12"""
    assert (e-s)%2==0
    out=bytearray(); flags=0; nf=0; pend=bytearray(); ht={}
    nw=(e-s)//2
    W=struct.unpack('<%dH'%nw,src[s:e])
    i=0
    while i<nw:
        best=0; bd=0
        if i+2<=nw:
            key=(W[i]<<16)|W[i+1]
            lo=max(0,i-4095)
            for cand in reversed(ht.get(key,())):
                if cand<lo: break
                l=0; maxl=min(17,nw-i)
                while l<maxl and W[cand+l]==W[i+l]: l+=1
                if l>best:
                    best=l; bd=i-cand
                    if l==17: break
        if best>=2:
            tok=bd|((best-2)<<12)
            pend+=bytes((tok&0xff,(tok>>8)&0xff)); n=best
        else:
            flags|=1<<nf; pend+=struct.pack('<H',W[i]); n=1
        nf+=1
        if nf==16:
            out+=struct.pack('<H',flags); out+=pend; flags=0; nf=0; pend=bytearray()
        for k in range(n):
            j=i+k
            if j+2<=nw: ht.setdefault((W[j]<<16)|W[j+1],[]).append(j)
        i+=n
    # Emit a zero-distance match, including a new flags word at 16-token boundaries.
    pend += b'\x00\x00'
    out += struct.pack('<H',flags); out += pend
    return bytes(out)

def _compress_chunk_v3_optimal(src,s,e):
    """Minimize token count; all v3 literals/matches cost one 16-bit word."""
    words=struct.unpack('<%dH'%((e-s)//2),src[s:e]); n=len(words)
    lengths=[0]*n; distances=[0]*n; ht={}
    for i in range(n-1):
        key=(words[i]<<16)|words[i+1]; limit=min(17,n-i)
        for j in reversed(ht.get(key,())):
            if i-j>4095: break
            length=2
            while length<limit and words[j+length]==words[i+length]: length+=1
            if length>lengths[i]: lengths[i]=length; distances[i]=i-j
            if length==limit: break
        ht.setdefault(key,[]).append(i)
    cost=[0]*(n+1); take=[1]*n
    for i in range(n-1,-1,-1):
        cost[i]=1+cost[i+1]
        for length in range(2,lengths[i]+1):
            value=1+cost[i+length]
            if value<=cost[i]: cost[i]=value; take[i]=length
    tokens=[]; i=0
    while i<n:
        length=take[i]
        tokens.append((length==1,words[i] if length==1 else distances[i]|((length-2)<<12)))
        i+=length
    tokens.append((False,0))
    out=bytearray()
    for i in range(0,len(tokens),16):
        group=tokens[i:i+16]; flags=sum(int(lit)<<j for j,(lit,_) in enumerate(group))
        out+=struct.pack('<H',flags)
        out+=struct.pack('<%dH'%len(group),*(word for _,word in group))
    return bytes(out)

def slz_compress_v3(data, template=None, optimal=False):
    """template: original 0x20-byte SLZ header to preserve unknown fields."""
    n=len(data); body=bytearray(); off=0
    while off<n:
        cu=min(CHUNK,n-off)
        encoder=_compress_chunk_v3_optimal if optimal else _compress_chunk_v3
        c=encoder(data,off,off+cu) if cu%2==0 else b'\xff'*(cu+1)
        if len(c)>=cu: body+=struct.pack('<H',cu & 0xffff)+data[off:off+cu]
        else:          body+=struct.pack('<H',len(c))+c
        off+=cu
    if template is not None and len(template) >= 32:
        h = bytearray(template[:32])          # keep every unknown field intact
    else:
        h = bytearray(32); h[0:4] = b'SLZ\x03'; h[5] = 1
        struct.pack_into('<H', h, 6, 0x25)
        struct.pack_into('<I', h, 0x14, 0x20); h[0x19] = CHUNK >> 10
    h[3] = 3                                   # we always emit v3
    struct.pack_into('<I', h, 8, len(body))
    struct.pack_into('<I', h, 12, n)
    return bytes(h) + bytes(body)
