"""Export a redistributable patch: xdelta3 diffs of every changed pack/record
against the ORIGINAL game data, plus the TOC diff.  No original game data is
included.  Output: release/payload/*.xd + release/payload/manifest.json

Layout decided here (see AGENTS.md):
  * a patched pack that fits its original slot  -> written in place
  * a pack that grows (always last pack of its TOC record) -> the whole record
    is appended to the end of its archive and the TOC record repointed
"""
import sys, json, struct, hashlib, subprocess, os, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT/'tools')); sys.path.insert(0, str(ROOT))
import build_reloc as br
from aska_toc import crypt12

XDELTA = str(br.GAME/'xdelta.exe')
OUT = ROOT/'release/payload'
sha = lambda b: hashlib.sha256(b).hexdigest()

def xd(old, new, name):
    with tempfile.TemporaryDirectory() as t:
        a, b = Path(t)/'a', Path(t)/'b'; a.write_bytes(old); b.write_bytes(new)
        subprocess.run([XDELTA, '-e', '-9', '-f', '-s', str(a), str(b), str(OUT/name)], check=True)
    return name

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for f in OUT.glob('*.xd'): f.unlink()
    man = json.loads((br.OUT/'manifest.json').read_text(encoding='utf-8'))
    size0, toc_raw = br.pristine()
    size1 = json.loads((br.STATE/'backup1.json').read_text())['size']
    toc = bytearray(crypt12(toc_raw)); recs = br.all_records(toc)
    ends = {0: size0, 1: size1}
    new = {(p['arc'], p['offset']): p for p in man['packs']}
    items = []; done = set()
    for (arc, off), p in sorted(new.items()):
        P = br.PACKSA[arc][p['pack']]; data = (br.OUT/p['file']).read_bytes()
        slot = (P['tot'] + 0x7ff) & ~0x7ff
        with br.ARCS[arc].open('rb') as f:
            f.seek(off); old = f.read(slot)
        if len(data) <= slot:
            data = data + bytes(slot - len(data))
            items.append({'mode': 'inplace', 'arc': arc, 'offset': off, 'length': slot,
                          'old_sha256': sha(old), 'new_sha256': sha(data),
                          'patch': xd(old, data, f'a{arc}_p{p["pack"]}.xd')})
            done.add((arc, off)); continue
        # grown: relocate every TOC record that contains it (records end with this pack)
        for o, n, b, st in recs:
            if (st >> 28) != arc: continue
            lo = (st & 0x0fffffff) * 0x800; hi = lo + b
            if not lo <= off < hi: continue
            with br.ARCS[arc].open('rb') as f:
                f.seek(lo); rec_old = f.read(b)
            rec_new = bytearray(rec_old[:off-lo]) + data
            others = [k for k in new if k[0] == arc and lo <= k[1] < hi and k[1] != off]
            for ka in others:   # other patched packs inside the same record keep their slots
                d2 = (br.OUT/new[ka]['file']).read_bytes(); s2 = ka[1] - lo
                rec_new[s2:s2+len(d2)] = d2
            rec_new = bytes(rec_new) + bytes((-len(rec_new)) % 0x800)
            start = (ends[arc] + 0x7ff) & ~0x7ff
            ends[arc] = start + len(rec_new)
            struct.pack_into('<3I', toc, o, len(rec_new)//0x800, len(rec_new), (arc << 28) | (start//0x800))
            items.append({'mode': 'append', 'arc': arc, 'source_offset': lo, 'source_length': b,
                          'offset': start, 'length': len(rec_new),
                          'old_sha256': sha(rec_old), 'new_sha256': sha(rec_new),
                          'patch': xd(rec_old, rec_new, f'a{arc}_r{o:x}.xd')})
            done.update(others); done.add((arc, off))
    # packs inside grown records were written there; drop their separate in-place items? keep: harmless
    toc_new = crypt12(bytes(toc))
    items.append({'mode': 'toc', 'arc': 0, 'offset': 0, 'length': len(toc_new),
                  'old_sha256': sha(toc_raw), 'new_sha256': sha(toc_new), 'patch': xd(toc_raw, toc_new, 'toc.xd')})
    meta = {'game': 'STAR OCEAN - THE LAST HOPE - 4K & Full HD Remaster (Steam 609150)',
            'original_sizes': {'0000.bin': size0, '0001.bin': size1},
            'patched_sizes': {'0000.bin': ends[0], '0001.bin': ends[1]},
            'messages': man['messages'], 'items': items}
    (OUT/'manifest.json').write_text(json.dumps(meta, indent=1), encoding='utf-8')
    total = sum((OUT/i['patch']).stat().st_size for i in items)
    print(f"{len(items)} items, payload {total/1e6:.1f} MB, growth 0000 {(ends[0]-size0)/1e6:.1f} MB, 0001 {(ends[1]-size1)/1e6:.1f} MB")

if __name__ == '__main__':
    main()
