import struct
def _chunk_v1(src,i,clen,cu,out):
    end=i+clen; tgt=len(out)+cu; fb=0; nb=0
    while len(out)<tgt:
        if nb==0:
            if i>=end: return
            fb=src[i]; i+=1; nb=8
        bit=fb&1; fb>>=1; nb-=1
        if bit:
            out.append(src[i]); i+=1
        else:
            b0=src[i]; b1=src[i+1]; i+=2
            dist=b0|((b1&0x0f)<<8)
            if dist==0: return
            ln=(b1>>4)+3; p=len(out)-dist
            for k in range(ln): out.append(out[p+k])
def _chunk_v2(src,i,clen,cu,out):
    end=i+clen; tgt=len(out)+cu; fb=0; nb=0
    while len(out)<tgt:
        if nb==0:
            if i>=end: return
            fb=src[i]; i+=1; nb=8
        bit=fb&1; fb>>=1; nb-=1
        if bit:
            out.append(src[i]); i+=1
        else:
            a=src[i]; c=src[i+1]
            dist=a|((c&0x0f)<<8); code=(c>>4)&0x0f
            if code<0xf:
                i+=2; ln=code+3; p=len(out)-dist
                for k in range(ln): out.append(out[p+k])
            else:
                if dist<0x100: fill=src[i+2]; cnt=dist+0x13; i+=3
                else:          fill=dist&0xff; cnt=(dist>>8)+3; i+=2
                out+=bytes([fill])*cnt
def _chunk_v3(src,i,clen,cu,out):
    end=i+clen; tgt=len(out)+cu; fw=0; nb=0
    while len(out)<tgt:
        if nb==0:
            if i+1>=end: return
            fw=src[i]|src[i+1]<<8; i+=2; nb=16
        bit=fw&1; fw>>=1; nb-=1
        if bit:
            out+=src[i:i+2]; i+=2
        else:
            raw=src[i]|src[i+1]<<8; i+=2
            dist=raw&0xfff
            if dist==0: return
            ln=(raw>>12)+2; p=len(out)-dist*2
            for k in range(ln): out+=out[p+2*k:p+2*k+2]
_H={1:_chunk_v1,2:_chunk_v2,3:_chunk_v3}
def slz_decompress(buf,off=0):
    if buf[off:off+3]!=b'SLZ': raise ValueError('not SLZ: %r'%buf[off:off+4])
    ver=buf[off+3]
    csize,usize=struct.unpack_from('<II',buf,off+8)
    hdrsz=struct.unpack_from('<I',buf,off+0x14)[0]
    cu_max=buf[off+0x19]<<10
    if ver not in _H: raise ValueError('unsupported SLZ ver %d'%ver)
    body=buf[off+hdrsz:off+hdrsz+csize]
    out=bytearray(); i=0
    if cu_max==0: cu_max=usize
    while len(out)<usize:
        cu=min(cu_max,usize-len(out))
        clen=body[i]|body[i+1]<<8; i+=2
        if clen==0 or clen==cu:
            out+=body[i:i+cu]; i+=cu
        else:
            _H[ver](body,i,clen,cu,out); i+=clen
    return bytes(out),i+hdrsz
