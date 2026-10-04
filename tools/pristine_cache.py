"""Keep a copy of the ORIGINAL bytes of every pack the patch touches, so builds
and release exports never depend on the (patched) game files again.

  python tools/pristine_cache.py snapshot   (game must be pristine: Steam verify first)

Cache: reloc/pristine/a<arc>_<offset hex>.bin = original pack slot bytes.
build_reloc.read_original() and export_release.py read from here when present.
"""
import sys, json, hashlib
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools')); sys.path.insert(0, str(ROOT))
CACHE = ROOT/'reloc/pristine'

def path(arc, off): return CACHE/f'a{arc}_{off:x}.bin'

def read(arc, off, length):
    p = path(arc, off)
    if p.exists():
        b = p.read_bytes()
        if len(b) >= length: return b[:length]
    return None

def snapshot():
    import build_reloc as br
    size0, toc = br.pristine()
    with br.ARCS[0].open('rb') as f:
        assert hashlib.sha256(f.read(0xC0000)).hexdigest() == hashlib.sha256(toc).hexdigest(), 'game is not pristine (run Steam verify)'
    CACHE.mkdir(parents=True, exist_ok=True)
    man = json.loads((br.OUT/'manifest.json').read_text(encoding='utf-8'))
    n = 0
    for p in man['packs']:
        arc, off = p.get('arc', 0), p['offset']
        P = br.PACKSA[arc][p['pack']]; slot = (P['tot'] + 0x7ff) & ~0x7ff
        if path(arc, off).exists(): continue
        with br.ARCS[arc].open('rb') as f:
            f.seek(off); path(arc, off).write_bytes(f.read(slot)); n += 1
    print(n, 'packs cached')

if __name__ == '__main__':
    snapshot()
