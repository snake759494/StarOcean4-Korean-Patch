"""Undo an applied release payload using the pristine cache (no Steam verify needed).
  python tools/unpatch.py   -> writes original pack bytes back, restores TOC and archive sizes,
                               then re-checks every old_sha256 of release/payload/manifest.json"""
import sys, json, hashlib
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools')); sys.path.insert(0, str(ROOT))
import build_reloc as br, pristine_cache
sha = lambda b: hashlib.sha256(b).hexdigest()

def main():
    if br.game_running(): raise SystemExit('Close the game first.')
    man = json.loads((ROOT/'release/payload/manifest.json').read_text(encoding='utf-8'))
    for it in man['items']:
        if it['mode'] != 'inplace': continue
        old = pristine_cache.read(it['arc'], it['offset'], it['length'])
        assert old is not None and sha(old) == it['old_sha256'], it['patch']
        with br.ARCS[it['arc']].open('r+b') as f:
            f.seek(it['offset']); f.write(old)
    br.restore()
    for it in man['items']:
        with br.ARCS[it['arc']].open('rb') as f:
            f.seek(it.get('source_offset', it['offset'])); b = f.read(it.get('source_length', it['length']))
        assert sha(b) == it['old_sha256'], ('still patched', it['patch'])
    print('pristine: all', len(man['items']), 'source regions match')

if __name__ == '__main__':
    main()
