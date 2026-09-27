import os,struct
from slz import slz_decompress
GAME=r"C:\Program Files (x86)\Steam\steamapps\common\STAR OCEAN - THE LAST HOPE - 4K & Full HD Remaster"
BIN0=os.path.join(GAME,"0000.bin")
_f=open(BIN0,'rb')
def read_entry0(off,size):
    _f.seek(off); raw=_f.read(size+0x40)
    return slz_decompress(raw)[0] if raw[:3]==b'SLZ' else raw[:size]
