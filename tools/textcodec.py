"""Decode/encode MCDp message token streams.
Tokens: ('g',char) glyph | ('nl',) newline | ('var',id,default_str) | ('ctl',b0,b1) unknown
"""
def decode_tokens(raw, g2c):
    toks=[]; j=0; n=len(raw)
    while j<n:
        b=raw[j]
        if b==0: break
        if b==0x93 and j+3<n and raw[j+1]==0x80 and raw[j+3]==0:
            vid=raw[j+2]; j+=4; s=[]
            while j<n and raw[j]!=0:
                gi=raw[j]-1; s.append(g2c[gi] if 0<=gi<len(g2c) else '\uFFFD'); j+=1
            j+=1; toks.append(('var',vid,''.join(s))); continue
        if b>=0x80:
            nb=raw[j+1] if j+1<n else 0
            toks.append(('nl',) if (b==0x80 and nb==0x80) else ('ctl',b,nb)); j+=2; continue
        gi=b-1; toks.append(('g', g2c[gi] if 0<=gi<len(g2c) else '\uFFFD')); j+=1
    return toks
def tokens_to_str(toks):
    out=[]
    for t in toks:
        if t[0]=='g': out.append(t[1])
        elif t[0]=='nl': out.append('\n')
        elif t[0]=='var': out.append('{V%d:%s}'%(t[1],t[2]))
        else: out.append('{C%02X%02X}'%(t[1],t[2]))
    return ''.join(out)
def str_to_tokens(s):
    toks=[]; i=0
    while i<len(s):
        c=s[i]
        if c=='\n': toks.append(('nl',)); i+=1; continue
        if c=='{':
            e=s.index('}',i); body=s[i+1:e]
            if body.startswith('V'):
                vid,dflt=body[1:].split(':',1); toks.append(('var',int(vid),dflt))
            else:
                toks.append(('ctl',int(body[1:3],16),int(body[3:5],16)))
            i=e+1; continue
        toks.append(('g',c)); i+=1
    return toks
def encode_tokens(toks, c2g):
    """c2g: dict char -> 1-based glyph index"""
    out=bytearray()
    for t in toks:
        if t[0]=='g': out.append(c2g[t[1]])
        elif t[0]=='nl': out+=b'\x80\x80'
        elif t[0]=='ctl': out+=bytes((t[1],t[2]))
        else:
            out+=bytes((0x93,0x80,t[1],0))
            for ch in t[2]: out.append(c2g[ch])
            out.append(0)
    out.append(0)
    return bytes(out)
def chars_in(toks):
    s=set()
    for t in toks:
        if t[0]=='g': s.add(t[1])
        elif t[0]=='var': s.update(t[2])
    return s
