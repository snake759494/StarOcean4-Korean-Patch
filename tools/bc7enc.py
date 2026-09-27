import numpy as np
W4=np.array([0,4,9,13,17,21,26,30,34,38,43,47,51,55,60,64],dtype=np.int32)

def encode_bc7_white_alpha4(alpha):
    """BC7 mode 5: opaque white color, four independent alpha values.

    The two-bit alpha index uses half the selector storage of mode 6.
    Alpha values are 0, 84, 171, 255 (BC7 two-bit interpolation weights).
    """
    height,width=alpha.shape
    assert height%4==0 and width%4==0
    blocks=alpha.reshape(height//4,4,width//4,4).transpose(0,2,1,3).reshape(-1,16).astype(np.int32)
    palette=np.array([0,84,171,255])
    idx=np.abs(blocks[:,:,None]-palette).argmin(axis=2).astype(np.uint64)
    swap=idx[:,0]>=2
    idx[swap]=3-idx[swap]
    a0=np.where(swap,255,0).astype(np.uint64)
    a1=np.where(swap,0,255).astype(np.uint64)
    lo=np.full(len(blocks),0x20|(((1<<42)-1)<<8),dtype=np.uint64)
    lo|=a0<<np.uint64(50)
    lo|=a1<<np.uint64(58)
    hi=a1>>np.uint64(6)
    # Color indices occupy bits 66..96 and are zero (identical endpoints).
    hi|=idx[:,0]<<np.uint64(33)
    for k in range(1,16):hi|=idx[:,k]<<np.uint64(32+2*k)
    out=np.empty((len(blocks),2),dtype='<u8');out[:,0]=lo;out[:,1]=hi
    return out.tobytes()
def encode_bc7_alpha(alpha, rgb=0, uniform_endpoints=False, alpha_levels=16):
    """Alpha mask and black/white RGB, encoded as BC7 mode 6.

    Shared RGBA endpoint p-bits give white RGB=254/255, exactly 255
    at alpha=255 endpoints. Alpha encoding is independent of this option.
    """
    assert rgb in (0,255)
    assert alpha_levels in (4,8,16)
    H,Wd=alpha.shape
    assert H%4==0 and Wd%4==0
    bh,bw=H//4,Wd//4
    b=alpha.reshape(bh,4,bw,4).transpose(0,2,1,3).reshape(-1,16).astype(np.int32)
    nb=b.shape[0]
    amin=b.min(axis=1); amax=b.max(axis=1)
    if uniform_endpoints:
        # Fixed endpoints share more compressed header bytes. Mode 6 keeps
        # 16 alpha levels; opacity rounding error is at most 10 out of 255.
        # Canonical endpoints also for flat blocks: their selector bits still
        # encode transparent/opaque pixels exactly, while headers repeat.
        amin=np.zeros_like(amin);amax=np.full_like(amax,255)
    vals=((amin[:,None]*(64-W4[None,:]) + amax[:,None]*W4[None,:] + 32)>>6)   # (nb,16)
    idx=np.empty((nb,16),dtype=np.int64)
    step=16384
    for s in range(0,nb,step):
        e=min(s+step,nb)
        d=np.abs(b[s:e,:,None]-vals[s:e,None,:])     # (n,16px,16w)
        if alpha_levels==8:
            # Symmetric palette preserves endpoint swaps and full opacity.
            d[:,:,[1,3,5,7,8,10,12,14]]=1000
        elif alpha_levels==4:
            d[:,:,[1,2,3,4,6,7,8,9,11,12,13,14]]=1000
        idx[s:e]=d.argmin(axis=2)
    # anchor: pixel0 index must be < 8 -> else swap endpoints
    swap=idx[:,0]>=8
    idx[swap]=15-idx[swap]
    e0=np.where(swap,amax,amin).astype(np.uint64)
    e1=np.where(swap,amin,amax).astype(np.uint64)
    P0=e0&1; A0=e0>>1
    P1=e1&1; A1=e1>>1
    lo=np.uint64(0x40)|(A0<<np.uint64(49))|(A1<<np.uint64(56))|(P0<<np.uint64(63))
    if rgb==255: lo |= np.uint64(((1<<42)-1)<<7)
    ix=idx.astype(np.uint64)
    hi=P1|((ix[:,0]&np.uint64(7))<<np.uint64(1))
    for k in range(1,16):
        hi|=ix[:,k]<<np.uint64(4*k)
    out=np.empty((nb,2),dtype='<u8'); out[:,0]=lo; out[:,1]=hi
    return out.tobytes()
