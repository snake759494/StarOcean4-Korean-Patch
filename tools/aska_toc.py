import struct
K=0x13578642; M=0xffffffff
def crypt12(buf):
    b=bytearray(buf); eax=K
    for p in range(0,len(b)-11,12):
        w=list(struct.unpack_from('<3I',b,p))
        w[0]^=eax; eax^=(eax*2)&M; w[1]^=eax
        eax=(~eax)&M; eax^=K; w[2]^=eax
        ecx=eax; eax=((eax*4)&M)^ecx^K; eax^=(eax*2)&M
        struct.pack_into('<3I',b,p,*w)
    return bytes(b)
def crypt16(buf):
    b=bytearray(buf); eax=K
    for p in range(0,len(b)-15,16):
        w=list(struct.unpack_from('<4I',b,p))
        w[0]^=eax; eax^=(eax*2)&M; w[1]^=eax
        eax=(~eax)&M; eax^=K; w[2]^=eax
        eax=((eax*4)&M)^eax; eax^=K; w[3]^=eax
        eax=(~eax)&M; eax^=K; eax^=(eax*2)&M
        struct.pack_into('<4I',b,p,*w)
    return bytes(b)
